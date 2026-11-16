USERS = [
    {'id': 1, 'name': 'Aoife', 'email': 'aoife@example.com',
     'password_hash': '5f4dcc3b5aa765d61d8327deb882cf99', 'active': True},
    {'id': 2, 'name': 'Jozef', 'email': 'jozef@example.com',
     'password_hash': '202cb962ac59075b964b07152d234b70', 'active': False},
]


def get_users(active_only=False):
    if active_only:
        return [u for u in USERS if u['active']]
    return USERS
