from os import getenv
from sys import setrecursionlimit

from dotenv import load_dotenv
from itd import ITDClient, ITDConfig, User
from itd.enums import RateLimitMode
from itd.logger import setup_logging, get_logger

from db import create_db
from models import User as UserModel

load_dotenv()
setup_logging('WARNING')
l = get_logger('scraper')
l.setLevel('DEBUG')
setrecursionlimit(3000)

c = ITDClient(getenv('TOKEN'), config=ITDConfig(RateLimitMode.MAX, 1, {'get_user': 3}))

db = create_db(getenv('DATABASE_URL', ''))

l.info('init')
users = set()
count = 0

def process_user(user: User, force: bool = False, recursion: int = 0):
    global count

    if user.id not in users and not db.query(UserModel).where(UserModel.user_id == user.id).first():
        db.add(UserModel(
            user_id=user.id,
            created_at=user.created_at,
            username=user.username,
            display_name=user.display_name,
            followers=user.followers_count,
            following=user.following_count,
            posts=user.posts_count,
            verified=user.verified,
            following_users=[following.id for following in user.following],
            followed_by_users=[follower.id for follower in user.followers],
            avatar=user.avatar
        ))
        l.info('[%s] add user %s', count, user.username)
        users.add(user.id)
    elif not force:
        l.debug('[%s] skip user %s', count, user.username)
        return
    if recursion > 990:
        l.debug('skip user %s (recursion)', user.username)
        return

    if count > 10:
        count = 0
        l.info('commit batch')
        db.commit()
    count += 1

    for follower in user.followers:
        process_user(follower, recursion=recursion + 1)

    for following in user.following:
        process_user(following, recursion=recursion + 1)

try:
    process_user(User('oxo'), True)
except KeyboardInterrupt:
    l.info('keyboard interrupt')
finally:
    db.commit()
    db.close()