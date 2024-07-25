from contextvars import ContextVar
import json
import jwt

from sanic.request import Request
from sanic.response import HTTPResponse, json, text
from sanic.views import HTTPMethodView
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import *
from database import async_session, async_engine
from models import User, Account, Transaction, Base
from auth_utils import generate_jwt, admin_required

_base_model_session_ctx = ContextVar("session")

@app.listener("before_server_start")
async def create_table(app):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@app.middleware("request")
async def check_jwt(request: Request):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token = auth_header.split()[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.ctx.user_id = payload['user_id']
            request.ctx.isAdmin = payload['isAdmin']
        except jwt.PyJWTError:
            pass

@app.middleware("request")
async def inject_session(request):
    try:
        request.ctx.session = async_session
        request.ctx.session_ctx_token = _base_model_session_ctx.set(request.ctx.session)
        # print(request.ctx.session)
    except Exception as e:
        print(f"Ошибка: {e}")
        raise

@app.middleware("response")
async def close_session(request, response):
    try:
        if hasattr(request.ctx, "session_ctx_token"):
            _base_model_session_ctx.reset(request.ctx.session_ctx_token)
            # request.ctx.session.close()
    except Exception as e:
        print(f"Ошибка: {e}")
        raise

@app.post("/add_user", ignore_body=False)
async def add_user(request):
    try:
        data = request.json
        full_name = data.get('full_name')
        email = data.get('email')
        password = data.get('password')
        if not full_name or not password or not email:
            return json({'error': 'full_name or password or email missing'}, status=400)
        try:
            async with request.ctx.session.begin() as conn:
                stmt = select(User).where(User.email.in_([email]))
                user_result = await conn.execute(stmt)
                user = user_result.scalar_one_or_none()
                if (user):
                    return json({'message': "Ошибка при создании пользователя: пользователь с такой почтой уже зарегистрирован"}, status=400)
                acc = Account(balance=0)
                user = User(full_name=full_name, email=email, password=password, accounts=[acc])
                conn.add(user)
                await conn.commit()
            return json({'message': user.to_dict()}, status=200)
        except Exception as e:
            return json({'message': f"Ошибка при создании пользователя: {e}"}, status=400)
    except:
        return json({'error': 'Invalid JSON'}, status=400)

@app.post("/add_admin", ignore_body=False)
async def add_admin(request):
    try:
        data = request.json
        full_name = data.get('full_name')
        email = data.get('email')
        password = data.get('password')
        if not full_name or not password or not email:
            return json({'error': 'full_name or password or email missing'}, status=400)
        try:
            async with request.ctx.session.begin() as conn:
                stmt = select(User).where(User.email.in_([email]))
                user_result = await conn.execute(stmt)
                user = user_result.scalar_one_or_none()
                if (user):
                    return json({'message': "Ошибка при создании администратора: вы уже зарегистрированы"}, status=400)
                user = User(full_name=full_name, email=email, password=password, isAdmin=True)
                conn.add(user)
                await conn.commit()
            return json({'message': user.to_dict()}, status=200)
        except Exception as e:
            return json({'message': f"Ошибка при создании администратора: {e}"}, status=400)
    except:
        return json({'error': 'Invalid JSON'}, status=400)

@app.get("/login", ignore_body=False)
async def login(request):
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        if not password or not email:
            return json({'error': 'password or email missing'}, status=400)
        try:
            async with request.ctx.session.begin() as conn:
                # session = request.ctx.session
                stmt = select(User).where(User.email.in_([email]))
                user_result = await conn.execute(stmt)
                user = user_result.scalar_one_or_none()
                if (user and user.password == password):
                    token = generate_jwt({'id': user.id, 'isAdmin': user.isAdmin})
                    return json({'token': token}, status=200)
        except Exception as e:
            return json({'message': f"Ошибка при идентификации пользователя: {e}"}, status=400)
    except:
        return json({'error': 'Invalid JSON'}, status=400)

@app.get("/user_info")
async def get_user_info(request):
    try:
        user_id = request.ctx.user_id
        session = request.ctx.session
        async with session.begin() as conn:
            stmt = select(User).where(User.id == user_id) #.options(selectinload(User.accounts))
            result = await conn.execute(stmt)
            user = result.scalar_one()
            return json(user.to_dict())
    except Exception as e:
        return json({'message': f"Ошибка при нахождении пользователя: {e}"}, status=400)

@app.get("/accounts_info")
async def get_accounts_info(request):
    try:
        user_id = request.ctx.user_id
        session = request.ctx.session
        async with session.begin() as conn:
            stmt = select(Account).where(Account.id_user == user_id) #.options(selectinload(User.accounts))
            result = await conn.execute(stmt)
            accounts = result.scalars().all()
            accounts_dicts = [account.to_dict() for account in accounts]
            return json(accounts_dicts)
    except Exception as e:
        return json({'message': f"Ошибка при нахождении счетов: {e}"}, status=400)

class UserView(HTTPMethodView):
    decorators=[admin_required]
    async def get(self, request):
        try:
            session = request.ctx.session
            async with session.begin() as conn:
                stmt = select(User).where(User.isAdmin == False)
                result = await conn.execute(stmt)
                users = result.scalars().all()
                users_dicts = [user.to_dict() for user in users]
                return json(users_dicts)
        except Exception as e:
            return json({'message': f"Ошибка при нахождении пользователя: {e}"}, status=400)
    async def post(self, request):
        resp = await add_user(request)
        return resp
app.add_route(UserView.as_view(), "/users")

@app.route('/test')
async def test(request):
    user_id = request.ctx.user_id
    isAdmin = request.ctx.isAdmin
    if user_id is None:
        return json({'error': 'Unauthorized'}, status=401)
    message = f"Welcome, user {user_id}"
    if (isAdmin):
        message = message + "\nyou are admin"
    return json({"message": message}, status=200)

if __name__ == '__main__':
    # asyncio.run(create_table())
    app.run(host='0.0.0.0', port=8000, debug=True)