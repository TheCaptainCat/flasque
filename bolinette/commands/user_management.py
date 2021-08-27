from bolinette import console
import getpass

import bolinette
from bolinette import Console, blnt
from bolinette import exceptions
from bolinette.decorators import command
from bolinette.exceptions import ParamConflictError, EntityNotFoundError, APIError, APIErrors


@command('user new', 'Add a user to the database', run_init=True)
@command.argument('argument', 'username', summary='The new user\'s username')
@command.argument('argument', 'email', summary='The new user\'s email')
@command.argument('option', 'roles', flag='r', summary='The user\'s roles, comma separated')
async def create_user(blnt: 'bolinette.Bolinette', username: str, email: str, roles: str = None):
    console = Console()
    user_service = blnt.context.service('user')
    role_service = blnt.context.service('role')
    while True:
        password = getpass.getpass('Choose password: ')
        password2 = getpass.getpass('Confirm password: ')
        if password == password2:
            break
        console.error('Passwords don\'t match')
    async with blnt.Transaction(blnt.context, print_error=False, propagate_error=False):
        user_roles = []
        if roles is not None:
            for role_name in [r.strip() for r in roles.split(',')]:
                try:
                    user_roles.append(await role_service.get_by_name(role_name))
                except EntityNotFoundError:
                    console.error(f'Role "{role_name}" does not exist')
                    exit(1)
        try:
            user = await user_service.create({
                'username': username,
                'password': password,
                'email': email
            })
            for role in user_roles:
                user.roles.append(role)
        except (APIError, APIErrors) as ex:
            if isinstance(ex, APIError):
                errors = [ex]
            else:
                errors = ex.errors
            for err in [err for err in errors if isinstance(err, ParamConflictError)]:
                console.error(f'Conflict: {err.message.split(":")[1]} already exists')
            exit(1)


@command('user list', 'Lists all usernames in database', run_init=True)
@command.argument('flag', 'roles', flag='r', summary='Prints user roles')
async def list_users(context: 'blnt.BolinetteContext', roles: bool):
    console = Console()
    user_service = context.service('user')
    for user in await user_service.get_all():
        roles_str = ''
        str_sep = ''
        if roles:
            roles_str = ','.join([r.name for r in user.roles])
            str_sep=':'
        console.print(user.username, roles_str, sep=str_sep)


@command('role list', 'Lists all usernames in database', run_init=True)
@command.argument('flag', 'users', flag='u', summary='Prints users assigned to each role')
async def list_roles(context: 'blnt.BolinetteContext', users: bool):
    console = Console()
    role_service = context.service('role')
    for role in await role_service.get_all():
        users_str = ''
        str_sep = ''
        if users:
            users_str = ','.join([r.username for r in role.users])
            str_sep=':'
        console.print(role.name, users_str, sep=str_sep)


@command('role assign', 'Assigns a user to a role', run_init=True)
@command.argument('argument', 'user', summary='The user\'s username')
@command.argument('argument', 'role', summary='The role\'s name')
@command.argument('flag', 'create', flag='c', summary='Create the role if it does not exist')
async def add_role(context: 'blnt.BolinetteContext', user: str, role: str, create: bool):
    console = Console()
    user_service = context.service('user')
    role_service = context.service('role')
    async with blnt.Transaction(context, print_error=False, propagate_error=False):
        try:
            user_ent = await user_service.get_by_username(user)
        except:
            console.error(f'User {user} does not exist')
            exit(1)
        role_ent = await role_service.get_by_name(role, safe=True)
        if role_ent is None:
            if create:
                role_ent = await role_service.create({'name': role})
                console.print(f'Created a new role: {role}')
            else:
                console.error(f'Role {role} does not exist')
                exit(1)
        if role_ent in user_ent.roles:
            console.print(f'User {user} is already assigned to role {role}')
            exit(1)
        user_ent.roles.append(role_ent)
    console.print(f'User {user} has been assigned to role {role}')


@command('role revoke', 'Rovokes a user from a role', run_init=True)
@command.argument('argument', 'user', summary='The user\'s username')
@command.argument('argument', 'role', summary='The role\'s name')
@command.argument('flag', 'prune', flag='p', summary='Deletes the role if noone is assigned to it')
async def revoke_role(context: 'blnt.BolinetteContext', user: str, role: str, prune: bool):
    console = Console()
    user_service = context.service('user')
    role_service = context.service('role')
    async with blnt.Transaction(context, print_error=False, propagate_error=False):
        try:
            user_ent = await user_service.get_by_username(user)
        except:
            console.error(f'User {user} does not exist')
            exit(1)
        try:
            role_ent = await role_service.get_first_by('name', role)
        except:
            console.error(f'Role {role} does not exist')
            exit(1)
        if role_ent not in user_ent.roles:
            console.error(f'User {user} is not assigned to role {role}')
            exit(1)
        user_ent.roles.remove(role_ent)
        console.print(f'User {user} has been rovoked from role {role}')
        if prune and len(role_ent.users) == 0:
            await role_service.delete(role_ent)
            console.print(f'Role {role} has been deleted')
