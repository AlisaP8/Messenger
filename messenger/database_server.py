from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import mapper, sessionmaker


class ServerStorage:
    class AllUsers:
        def __init__(self, username):
            self.name = username
            self.last_login = datetime.now()
            self.id = None

    class LoginHistory:
        def __init__(self, name, date, ip, port):
            self.id = None
            self.name = name
            self.date = date
            self.ip = ip
            self.port = port

    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None

    def __init__(self):
        self.engine = create_engine('sqlite:///server_base.db3', echo=False, pool_recycle=7200)
        self.metadata = MetaData()

        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime),
                            )

        user_history = Table('history', self.metadata,
                             Column('id', Integer, primary_key=True),
                             Column('name', ForeignKey('Users.id')),
                             Column('date', DateTime),
                             Column('ip', String),
                             Column('port', String),
                             )

        active_users_table = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id')),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime),
                                   )

        self.metadata.create_all(self.engine)

        mapper(self.AllUsers, users_table)
        mapper(self.LoginHistory, user_history)
        mapper(self.ActiveUsers, active_users_table)

        sess = sessionmaker(bind=self.engine)
        self.sess = sess()

        self.sess.query(self.ActiveUsers).delete()
        self.sess.commit()

    def user_login(self, username, ip_address, port):
        res = self.sess.query(self.AllUsers).filter_by(name=username)

        if res.count():
            user = res.first()
            user.last_login = datetime.now()
        else:
            user = self.AllUsers(username)
            self.sess.add(user)
            self.sess.commit()

        user_history = self.LoginHistory(user.id, datetime.now(), ip_address, port)
        self.sess.add(user_history)

        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.now())
        self.sess.add(new_active_user)

        self.sess.commit()

    def user_logout(self, username):
        user = self.sess.query(self.AllUsers).filter_by(name=username).first()

        self.sess.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.sess.commit()

    def users_list(self):
        query = self.sess.query(self.AllUsers.name, self.AllUsers.last_login)
        return query.all()

    def active_users_list(self):
        query = self.sess.query(
            self.AllUsers.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time,
        ).join(self.AllUsers)

        return query.all()

    def login_history(self, username=None):
        query = self.sess.query(
            self.AllUsers.name,
            self.LoginHistory.date,
            self.LoginHistory.ip,
            self.LoginHistory.port,
        ).join(self.AllUsers)

        if username:
            query = query.filter(self.AllUsers.name == username)

        return query.all()


if __name__ == '__main__':
    test_db = ServerStorage()
    test_db.user_login('client_1', '192.125.1.10', 80)
    test_db.user_login('client_2', '192.152.1.8', 7777)

    print(10 * '-', 'active_users_list()', 10 * '-')
    print(test_db.active_users_list())

    test_db.user_logout('client_1')

    print(10 * '-', 'active_users_list() after logout client_1', 10 * '-')
    print(test_db.active_users_list())

    print(10 * '-', 'login_history(client_1)', 10 * '-')
    print(test_db.login_history('client_1'))

    print(10 * '-', 'users_list()', 10 * '-')
    print(test_db.users_list())
