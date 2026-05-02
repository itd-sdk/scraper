from os import getenv
from sys import setrecursionlimit
from json import load

from dotenv import load_dotenv
from itd import ITDClient, ITDConfig, User
from itd.enums import RateLimitMode
from itd.logger import setup_logging, get_logger
from itd.exceptions import TargetUserBannedError, NotFoundError

from db import create_db
from models import User as UserModel

load_dotenv()
setup_logging('WARNING')
l = get_logger('updater')
l.setLevel('INFO')
setrecursionlimit(3000)

c = ITDClient(getenv('TOKEN'), config=ITDConfig(RateLimitMode.MAX, 1, {'get_user': 3}))

db = create_db(getenv('DATABASE_URL', ''))

l.info('init')
users = set()

with open('itdp.json', 'r') as fl:
    itdp = load(fl)

def update_user(user: UserModel):
    try:
        user_itd = User(user.user_id)
    except (TargetUserBannedError, NotFoundError):
        l.warning('user not found %s', user.username)
        user.exists = False
        db.commit()
        return

    user.username = user_itd.username
    user.display_name = user_itd.display_name
    user.followers = user_itd.followers_count or 0
    user.following = user_itd.following_count or 0
    user.posts = user_itd.posts_count or 0
    user.verified = user_itd.verified
    user.has_itdp = user_itd.id in itdp
    user.following_users = [following.id for following in user_itd.following] # pyright: ignore[reportAttributeAccessIssue]
    user.followed_by_users = [following.id for following in user_itd.followers] # pyright: ignore[reportAttributeAccessIssue]
    user.avatar = user_itd.avatar
    l.info('update user %s', user.username)
    db.commit()

for user in db.query(UserModel).all():
    update_user(user)