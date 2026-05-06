from os import getenv
from sys import setrecursionlimit
from json import load
from uuid import UUID

from dotenv import load_dotenv
from itd import ITDClient, ITDConfig, User
from itd.enums import RateLimitMode
from itd.logger import setup_logging, get_logger

from db import create_local_db, commit_with_retry
from models import User as UserModel

load_dotenv()
setup_logging('WARNING')
l = get_logger('scraper')
l.setLevel('DEBUG')
setrecursionlimit(3000)

c = ITDClient(getenv('BOT_TOKEN'), config=ITDConfig(RateLimitMode.MAX, 1, {'get_user': 5}))

# db = create_db(getenv('DATABASE_URL', ''))
db = create_local_db()

l.info('init')
users = set()

with open('itdp.json', 'r') as fl:
    itdp = load(fl)

def create_user(id: UUID, parent: str):
    global count

    if id not in users and not db.query(UserModel).where(UserModel.user_id == id).first():
        user = User(id)
        model = UserModel(
            user_id=user.id,
            created_at=user.created_at,
            username=user.username,
            display_name=user.display_name,
            followers=user.followers_count,
            following=user.following_count,
            posts=user.posts_count,
            verified=user.verified,
            following_users=str([following.id for following in user.following]),
            followed_by_users=str([follower.id for follower in user.followers]),
            avatar=user.avatar,
            has_itdp=str(user.id) in itdp
        )
        db.add(model)
        commit_with_retry(db)
        users.add(user.id)

        l.info('add user %s parent=%s', user.username, parent)
        return model
    else:
        l.debug('skip user %s parent=%s', id, parent)

def process_user(user: UserModel):
    for follower in eval(user.followed_by_users):
        model = create_user(follower, user.username)
        if model:
            process_user(model)

    for following in eval(user.following_users):
        model = create_user(following, user.username)
        if model:
            process_user(model)

try:
    for user in db.query(UserModel).offset(100).limit(1000).all():
        process_user(user)

except KeyboardInterrupt:
    l.info('keyboard interrupt')
finally:
    db.close()