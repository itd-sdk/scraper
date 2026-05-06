from os import getenv
from json import load
from random import choice
from string import ascii_lowercase, digits

from dotenv import load_dotenv
from itd import ITDClient, ITDConfig
from itd.enums import RateLimitMode
from itd.logger import setup_logging, get_logger
from db import create_local_db, commit_with_retry
from models import User as UserModel

load_dotenv()
setup_logging('WARNING')
l = get_logger('searcher')
l.setLevel('INFO')

c = ITDClient(getenv('BOT_TOKEN'), config=ITDConfig(RateLimitMode.MAX, 1, {'get_user': 3}))
db = create_local_db()

with open('itdp.json', 'r') as fl:
    itdp = load(fl)

def search(code: str):
    l.info('search %s', code)
    users, _ = c.search(code, 1)

    for user in users:
        if not db.query(UserModel).where(UserModel.user_id == user.id).first():
            l.info('add user %s', user.username)
            db.add(UserModel(
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
            ))
            commit_with_retry(db)
        else:
            l.debug('skip user %s', user.username)

while True:
    code = ''
    for i in range(4):
        code += choice(''.join(ascii_lowercase + digits))

    search(code)