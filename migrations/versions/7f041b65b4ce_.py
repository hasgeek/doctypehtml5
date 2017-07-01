"""empty message

Revision ID: 7f041b65b4ce
Revises: 
Create Date: 2017-06-28 15:55:41.212533

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.sql import table, column, select
import uuid
import base64
from progressbar import ProgressBar
import progressbar.widgets


revision = '7f041b65b4ce'
down_revision = None
branch_labels = None
depends_on = None


user_table = table('user', column('id', sa.Integer()),
    column('uid', sa.String(22)),
    column('uuid', sqlalchemy_utils.types.uuid.UUIDType(binary=False)))

conn = op.get_bind()


def b64_to_uuid(val):
    padding = '=='
    return uuid.UUID(bytes=base64.b64decode(val.replace(',', '+').replace('-', '/') + padding))


def uuid_to_b64(val):
    return base64.b64encode(val.bytes, altchars=',-').replace('=', '')

def get_progressbar(label, maxval):
    return ProgressBar(maxval=maxval,
        widgets=[
            label, ': ',
            progressbar.widgets.Percentage(), ' ',
            progressbar.widgets.Bar(), ' ',
            progressbar.widgets.ETA(), ' '
            ])


def upgrade():
    op.add_column('user', sa.Column('uuid', sqlalchemy_utils.types.uuid.UUIDType(binary=False), nullable=True))
    op.create_unique_constraint('user_uuid_key', 'user', ['uuid'])
    users = conn.execute(sa.select([user_table.c.id, user_table.c.uid, user_table.c.uuid]))

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_table))
    progress = get_progressbar("User", count)
    progress.start()

    for counter, user in enumerate(users):
        conn.execute(sa.update(
            user_table).where(user_table.c.id == user.id).values(uuid=b64_to_uuid(user.uid)))
        progress.update(counter)
    progress.finish()
    op.alter_column('user', 'uuid',
        existing_type=sqlalchemy_utils.types.uuid.UUIDType(binary=False),
        nullable=False)
    op.drop_column('user', 'uid')


def downgrade():
    op.add_column('user', sa.Column('uid', sa.VARCHAR(length=22), autoincrement=False, nullable=True))
    op.drop_constraint('user_uuid_key', 'user', type_='unique')
    op.create_unique_constraint(u'user_uid_key', 'user', ['uid'])
    users = conn.execute(sa.select([user_table.c.id, user_table.c.uid, user_table.c.uuid]))

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_table))
    progress = get_progressbar("User", count)
    progress.start()

    for counter, user in enumerate(users):
        conn.execute(sa.update(
            user_table).where(user_table.c.id == user.id).values(uid=uuid_to_b64(user.uuid)))
        progress.update(counter)
    progress.finish()

    op.alter_column('user', 'uid',
        existing_type=sa.String(22),
        nullable=False)
    op.drop_column('user', 'uuid')
