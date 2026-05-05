from os import getenv
from sys import setrecursionlimit
from json import load
from uuid import UUID

from dotenv import load_dotenv
from itd import ITDClient, ITDConfig, User
from itd.enums import RateLimitMode
from itd.logger import setup_logging, get_logger

from db import create_db, create_local_db
from models import User as UserModel

load_dotenv()
setup_logging('WARNING')
l = get_logger('scraper')
l.setLevel('DEBUG')
setrecursionlimit(3000)

c = ITDClient(getenv('BOT_TOKEN'), config=ITDConfig(RateLimitMode.MAX, 1, {'get_user': 3}))

db = create_db(getenv('DATABASE_URL', ''))
local_db = create_local_db()

l.info('init')
users = set()
count = 0

with open('itdp.json', 'r') as fl:
    itdp = load(fl)

def create_user(id: UUID, parent: str):
    global count

    if id not in users and not local_db.query(UserModel).where(UserModel.user_id == id).first():
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
        local_db.add(model)
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
            avatar=user.avatar,
            has_itdp=str(user.id) in itdp
        ))

        l.info('add user %s parent=%s', user.username, parent)
        count += 1
        users.add(user.id)
        return model
    else:
        l.debug('skip user %s parent=%s', id, parent)

def process_user(user: UserModel):
    global count

    if count > 10:
        count = 0
        l.info('commit batch')
        db.commit()

    for follower in eval(user.followed_by_users):
        model = create_user(follower, user.username)
        if model:
            process_user(model)

    for following in eval(user.following_users):
        model = create_user(following, user.username)
        if model:
            process_user(model)

try:
    for user in local_db.query(UserModel).offset(100).limit(1000).all():
        process_user(user)
except KeyboardInterrupt:
    l.info('keyboard interrupt')
finally:
    local_db.commit()
    local_db.close()
    db.commit()
    db.close()