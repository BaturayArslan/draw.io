from quart import Blueprint, g, current_app, jsonify, make_response, request
from flask_jwt_extended import jwt_required, get_jwt
from bson import ObjectId

from drawProject import db
from ..exceptions import DbError, BadRequest

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/profile', methods=['GET'])
@jwt_required()
async def user_profile():
    try:
        arguments = request.args
        user_id = arguments.get('user_id', None)
        if not user_id:
            return jsonify({'status': 'error', 'message': 'user_id parameter missing.'}), 400
        user_info = await db.get_user_profile(user_id)
        return jsonify({
            'status': 'success',
            'message': user_info
        })
    except DbError as e:
        jsonify({
            'status': 'error',
            'message': f'{str(e)}'
        }), 400
    except Exception as e:
        raise e


@user_bp.route('/add_friend', methods=['GET'])
@jwt_required()
async def add_friend():
    try:
        user = get_jwt()
        arguments = request.args
        friend_id = arguments.get('friend_id', None)
        avatar = arguments.get('avatar', None)
        if not (friend_id and avatar):
            return jsonify({'status': 'error', 'message': 'friend_id or avatar parameter missing.'}), 400
        await db.add_friend(user['_id'], friend_id, avatar)
        updated_friends = await db.find_user(user['email'], {'_id': 0, 'friends': 1})
        return jsonify({
            'status': 'success',
            'message': updated_friends
        })
    except DbError as e:
        jsonify({
            'status': 'error',
            'message': f'{str(e)}'
        }), 500
    except Exception as e:
        raise e


@user_bp.route('/delete_friend', methods=['GET'])
@jwt_required()
async def add_friend():
    try:
        user = get_jwt()
        arguments = request.args
        friend_id = arguments.get('friend_id', None)
        if not friend_id:
            return jsonify({'status': 'error', 'message': 'friend_id parameter missing.'}), 400
        await db.delete_friend(user['_id'], friend_id)
        updated_friends = await db.find_user(user['email'], {'_id': 0, 'friends': 1})
        return jsonify({
            'status': 'success',
            'message': updated_friends
        })
    except DbError as e:
        jsonify({
            'status': 'error',
            'message': f'{str(e)}'
        }), 500
    except Exception as e:
        raise e


@user_bp.route('/send_message', methods=['GET'])
@jwt_required()
async def send_message():
    try:
        user = get_jwt()
        message = await request.get_json()
        friend_id = message.get('friend_id', None)
        msg = message.get('msg', None)
        timestamp = message.get('timestamp', None)
        if not (friend_id or msg or timestamp) or (msg == '' or timestamp == ''):
            return jsonify({'status': 'error', 'message': 'friend_id or msg or timestamp parameter missing.'}), 400
        await db.send_message(user['id'], friend_id, message)
        await g.redis_connection.publish(user['id'])
        return jsonify({
            'status': 'success',
            'message': 'message deliverid.'
        })
    except DbError as e:
        jsonify({
            'status': 'error',
            'message': f'{str(e)}'
        }), 500
    except Exception as e:
        raise e

@user_bp.route('/get_messages', methods=['GET'])
@jwt_required()
async def get_messages():
    try:
        user = get_jwt()
        arguments = request.args
        friend_id = arguments.get('friend_id', None)
        if not friend_id:
            return jsonify({'status': 'error', 'message': 'friend_id parameter missing.'}), 400
        messages = await db.get_messages(user['id'], friend_id)
        return jsonify({
            'status':'success',
            'message': messages
        })
    except DbError as e:
        jsonify({
            'status': 'error',
            'message': f'{str(e)}'
        }), 500
    except Exception as e:
        raise e


@user_bp.route('/update_messages', methods=['GET'])
@jwt_required()
async def update_messages():
    try:
        user = get_jwt()
        arguments = request.args
        friend_id = arguments.get('friend_id', None)
        if not friend_id:
            return jsonify({'status': 'error', 'message': 'friend_id parameter missing.'}), 400

    except DbError as e:
        jsonify({
            'status': 'error',
            'message': f'{str(e)}'
        }), 500
    except Exception as e:
        raise e