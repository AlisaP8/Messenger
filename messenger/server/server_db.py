from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, ForeignKey, DateTime, String, Text
from sqlalchemy.orm import mapper, sessionmaker


class ServerStorage:
    class AllUsers:
        def __init__(self, username, passwd_hash):
            self.name = username
            self.last_login = datetime.now()
            self.passwd_hash = passwd_hash
            self.pubkey = None
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
            self.id = None
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time

    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        self.engine = create_engine(f'sqlite:///{path}', echo=False,
                                    pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime),
                            Column('passwd_hash', String),
                            Column('pubkey', Text),
                            )

        user_login_history = Table('Login_history', self.metadata,
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

        contacts_table = Table('Contacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('user', ForeignKey('Users.id')),
                               Column('contact', ForeignKey('Users.id')),
                               )

        users_history_table = Table('History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('sent', Integer),
                                    Column('accepted', Integer),
                                    )

        self.metadata.create_all(self.engine)

        mapper(self.AllUsers, users_table)
        mapper(self.LoginHistory, user_login_history)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.UsersContacts, contacts_table)
        mapper(self.UsersHistory, users_history_table)

        Sess = sessionmaker(bind=self.engine)
        self.sess = Sess()

        self.sess.query(self.ActiveUsers).delete()
        self.sess.commit()

    def user_login(self, username, ip_address, port, key):
        res = self.sess.query(self.AllUsers).filter_by(name=username)

        if res.count():
            user = res.first()
            user.last_login = datetime.now()
            if user.pubkey != key:
                user.pubkey = key
        else:
            # user = self.AllUsers(username)
            # self.sess.add(user)
            # self.sess.commit()
            # user_in_history = self.UsersHistory(user.id)
            # self.sess.add(user_in_history)
            raise ValueError('Пользователь не зарегистрирован')

        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.now())
        self.sess.add(new_active_user)

        user_history = self.LoginHistory(user.id, datetime.now(), ip_address, port)
        self.sess.add(user_history)

        self.sess.commit()

    def add_user(self, name, passwd_hash):
        user_row = self.AllUsers(name, passwd_hash)
        self.sess.add(user_row)
        self.sess.commit()
        history_row = self.UsersHistory(user_row.id)
        self.sess.add(history_row)
        self.sess.commit()

    def remove_user(self, name):
        user = self.sess.query(self.AllUsers).filter_by(name=name).first()
        self.sess.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.sess.query(self.LoginHistory).filter_by(name=user.id).delete()
        self.sess.query(self.UsersContacts).filter_by(user=user.id).delete()
        self.sess.query(
            self.UsersContacts).filter_by(
            contact=user.id).delete()
        self.sess.query(self.UsersHistory).filter_by(user=user.id).delete()
        self.sess.query(self.AllUsers).filter_by(name=name).delete()
        self.sess.commit()

    def get_hash(self, name):
        user = self.sess.query(self.AllUsers).filter_by(name=name).first()
        return user.passwd_hash

    def get_pubkey(self, name):
        user = self.sess.query(self.AllUsers).filter_by(name=name).first()
        return user.pubkey

    def check_user(self, name):
        if self.sess.query(self.AllUsers).filter_by(name=name).count():
            return True
        else:
            return False

    def user_logout(self, username):
        user = self.sess.query(self.AllUsers).filter_by(name=username).first()

        self.sess.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.sess.commit()

    def process_message(self, sender, rec):
        sender = self.sess.query(self.AllUsers).filter_by(name=sender).first().id
        rec = self.sess.query(self.AllUsers).filter_by(name=rec).first().id
        sender_row = self.sess.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        rec_row = self.sess.query(self.UsersHistory).filter_by(user=rec).first()
        rec_row.accepted += 1

        self.sess.commit()

    def add_contact(self, user, contact):
        user = self.sess.query(self.AllUsers).filter_by(name=user).first()
        contact = self.sess.query(self.AllUsers).filter_by(name=contact).first()

        if not contact or self.sess.query(self.UsersContacts).filter_by(
                user=user.id, contact=contact.id).count():
            return

        contact_row = self.UsersContacts(user.id, contact.id)
        self.sess.add(contact_row)
        self.sess.commit()

    def remove_contact(self, user, contact):

        user = self.sess.query(self.AllUsers).filter_by(name=user).first()
        contact = self.sess.query(self.AllUsers).filter_by(name=contact).first()

        if not contact:
            return

        self.sess.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id).delete()
        self.sess.commit()

    def users_list(self):
        query = self.sess.query(self.AllUsers.name,
                                self.AllUsers.last_login)
        return query.all()

    def active_users_list(self):
        query = self.sess.query(self.AllUsers.name,
                                self.ActiveUsers.ip_address,
                                self.ActiveUsers.port,
                                self.ActiveUsers.login_time,
                                ).join(self.AllUsers)

        return query.all()

    def login_history(self, username=None):
        query = self.sess.query(self.AllUsers.name,
                                self.LoginHistory.date,
                                self.LoginHistory.ip,
                                self.LoginHistory.port,
                                ).join(self.AllUsers)

        if username:
            query = query.filter(self.AllUsers.name == username)

        return query.all()

    def get_contacts(self, username):
        user = self.sess.query(self.AllUsers).filter_by(name=username).one()

        query = self.sess.query(self.UsersContacts, self.AllUsers.name). \
            filter_by(user=user.id).join(self.AllUsers,
                                         self.UsersContacts.contact == self.AllUsers.id)

        return [contact[1] for contact in query.all()]

    def message_history(self):
        query = self.sess.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        return query.all()


if __name__ == '__main__':
    test_db = ServerStorage('server_base.db3')
    test_db.user_login('Валя', '192.125.1.10', 8080)
    test_db.user_login('Петя', '192.152.1.8', 7777)
    print(test_db.users_list())
    test_db.process_message('Валя', '1111')
    print(test_db.message_history())
