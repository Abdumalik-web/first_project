from datetime import datetime
from aiogram.types import Message, Chat, User, MessageEntity, MessageOriginChannel
from bot import find_violation

chat = Chat(id=-100, type="supergroup")
u = User(id=1, is_bot=False, first_name="A")

def m(text, entities=None, **kw):
    return Message(message_id=1, date=datetime.now(), chat=chat, from_user=u, text=text, entities=entities, **kw)

assert find_violation(m("salom hammaga")) is None
assert find_violation(m("bu yerga kiring https://t.me/abc", [MessageEntity(type="url", offset=14, length=17)])) == "havola"
assert find_violation(m("instagram.com/xyz ga obuna")) == "havola"
assert find_violation(m("youtu.be/abc")) == "havola"
assert find_violation(m("t . me/kanal")) == "havola"
assert find_violation(m("@reklama_kanal", [MessageEntity(type="mention", offset=0, length=14)])) == "@username"
assert find_violation(m("bos", [MessageEntity(type="text_link", offset=0, length=3, url="https://instagram.com/x")])) == "havola"
fo = MessageOriginChannel(date=datetime.now(), chat=Chat(id=-200, type="channel"), message_id=5)
assert find_violation(m("hi", forward_origin=fo)) == "forward"
print("OK")
