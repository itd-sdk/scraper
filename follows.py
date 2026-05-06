from os import getenv
from sys import setrecursionlimit
from json import load

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
count = 0

with open('itdp.json', 'r') as fl:
    itdp = load(fl)

def process_user(user: User, force: bool = False, recursion: int = 0):
    global count

    if user.id in users:
        return
    if not db.query(UserModel).where(UserModel.user_id == user.id).first():
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
        l.info('[%s] add user %s', recursion, user.username)
        count += 1
    elif not force:
        l.debug('[%s] skip user %s', recursion, user.username)
        # return

    users.add(user.id)

    if count > 10:
        count = 0
        l.info('commit batch')
        commit_with_retry(db)

    for follower in user.followers:
        process_user(follower, recursion=recursion + 1)

    for following in user.following:
        process_user(following, recursion=recursion + 1)

try:
    process_user(User('nowkie'), True)
except KeyboardInterrupt:
    l.info('keyboard interrupt')
finally:
    commit_with_retry(db)
    db.close()
