import asyncio
import json
from quart import g,current_app,websocket,Blueprint,jsonify
from flask_jwt_extended import decode_token,get_jwt,jwt_required

from drawProject import db
from drawProject import redis
from drawProject.exceptions import DbError,CheckFailed

websocket_bp = Blueprint("websocket", __name__, url_prefix="/ws")

async def join_room(room_id,user):
    try:
        args = websocket.args.to_dict()
        room_info = await db.find_room(room_id)
        if websocket.args.get('password','') != room_info['status']['password'] and room_info['status']['is_start'] is True and len(room_info.get('users',[])) >= room_info['max_user'] :
            return jsonify({
                'status': 'error',
                'message': 'Couldnt Join Room.Room is full or game is start'
            }), 202
        for room_user in room_info.get('users',[]):
            if str(room_user['_id']) == user['user_id']:
                return jsonify({
                    'status': 'error',
                    'message': 'Your are already in this room.'
                }), 202
        await db.join_user_to_room(user['user_id'], room_id, room_info)
        await db.check_user(user['user_id'])

        # Publish an event for refresh_room_info view subscribers.
        redis.Events.set_user_join(room_id)
        await g.redis_connection.publish('rooms_info_feed', json.dumps(redis.Events.USER_JOIN))

        return True

    except DbError as e:
        return jsonify({"status": "error", "message": f"{str(e)}"}), 500
    except CheckFailed as e:
        await db.leave_user_from_room(user['user_id'],room_id)
        return jsonify({"status": "error", "message": f"{str(e)}"}), 500
    except Exception as e:
        raise e

async def leave_room(user,room_id):

    #TODO :: Save user stats  to database before leave
    pubsub,redis_connection = await redis.get_redis()
    result = await db.leave_user_from_room(user['user_id'],room_id)

    # Publish an event for refresh_room_info view subscribers.
    redis.Events.set_user_laeves(room_id)
    await g.redis_connection.publish('rooms_info_feed', json.dumps(redis.Events.USER_LEAVES))

    return True

@websocket_bp.websocket('/room/<string:room_id>')
async def ws(room_id):
    try:
        headers = websocket.headers
        token = headers['Authorization'].split('Bearer ')[1]
        user = decode_token(token)

        await redis.get_redis()

        await join_room(room_id,user)

        game = current_app.games[room_id]
        receive_task,send_task = await game.register(user['user_id'],user['user_name'],websocket)
        await receive_task
        await send_task
    except asyncio.CancelledError as e:
        # Clean up when user disconnect.
        try:
            print('clean up ')
            await leave_room(user,room_id)
            await game.disconnect(user['user_id'],user['user_name'])
            await _cancel_task((receive_task,send_task),raise_exp=True)
            raise
        except (KeyError,DbError):
            pass
        except Exception as e:
            return jsonify({"status": "error", "message": f"{str(e)}"}), 500
    except Exception as e:
        return jsonify({'status':'error','message': f'{str(e)}'},500)

async def _cancel_task(tasks,raise_exp=False):
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks,return_exceptions=True)
    if raise_exp:
        _raise_exceptions(tasks)

def _raise_exceptions(tasks):
    # Raise any unexpected exceptions
    for task in tasks:
        if not task.cancelled() and task.exception() is not None:
            raise task.exception()
