import re, os, sys


def validate_user(user_data):
    # Check email format
    email = user_data['email'].strip()
    if not email:
        raise ValueError("Email required")

    # Basic email validation
    if '@' not in email:
        raise ValueError('Invalid email')

    # Check username
    if not user_data.get('username'):
        raise ValueError("Username required")

    return True


def validate_age( age ):
    # chekc the age is ok
    if age == None:
        raise ValueError("Age required")
    if age<0 or age>150 :
        raise ValueError('Invalid age')
    return True


def old_validate(user_data):
    # TODO remove - not used anymore
    return validate_user(user_data)
