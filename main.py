from os import getenv

from dotenv import load_dotenv
from itd import ITDClient, ITDConfig, User
from itd.enums import RateLimitMode
from itd.logger import setup_logging, get_logger

from db import create_db
from models import User as UserModel

load_dotenv()
setup_logging('WARNING')
l = get_logger('scraper')
l.setLevel('INFO')

c = ITDClient(getenv('TOKEN'), config=ITDConfig(RateLimitMode.MAX, 1, {'get_user': 3}))

db = create_db(getenv('DATABASE_URL', ''))

users = {user.user_id for user in db.query(UserModel).all()}
count = 0

def process_user(user: User, force: bool = False):
    global count

    if user.id not in users:
        db.add(UserModel(
            user_id=user.id,
            created_at=user.created_at,
            username=user.username,
            display_name=user.display_name,
            followers=user.followers_count,
            following=user.following_count,
            posts=user.posts_count,
            verified=user.verified
        ))
        l.info('add user %s', user.username)
        users.add(user.id)
    elif not force:
        l.debug('skip user %s', user.username)
        return

    if count > 50:
        count = 0
        l.info('commit batch')
        db.commit()
    count += 1

    for follower in user.followers:
        process_user(follower)

    for following in user.following:
        process_user(following)

try:
    process_user(User('likebot2'), True)
except KeyboardInterrupt:
    l.info('keyboard interrupt')
finally:
    db.commit()
    db.close()