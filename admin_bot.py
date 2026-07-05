from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import os
import json

# المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN = "8741135682:AAEW-c-3D9NGPCwtnFsG35BYOz0yZtGjqj0"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

TREE_FILE = os.path.join(BASE_DIR, "store_tree.json")
DISCOUNTS_FILE = os.path.join(BASE_DIR, "discounts.json")
USERS_FILE = os.path.join(BASE_DIR, "users.txt")

class AdminStates(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_user_id = State()
    waiting_discount = State()
    waiting_broadcast = State()
    waiting_direct_id = State()
    waiting_direct_text = State()

def load_json(file, default):
    if not os.path.exists(file): return default
    with open(file, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

def get_tree():
    return load_json(TREE_FILE, {"type": "folder", "children": {}})

def update_tree(data):
    save_json(TREE_FILE, data)

def get_node_by_path(path):
    data = get_tree()
    if path == "root" or not path: return data
    curr = data
    keys = path.split(">")
    for key in keys:
        if "children" not in curr: curr["children"] = {}
        curr = curr["children"].setdefault(key, {"type": "folder", "children": {}})
    return curr

def add_to_tree(path, name, type, price=0):
    data = get_tree()
    target = data
    if path != "root":
        keys = path.split(">")
        for key in keys:
            target = target.setdefault("children", {}).setdefault(key, {"type": "folder", "children": {}})
    target.setdefault("children", {})[name] = {"type": type, "children": {} if type == "folder" else None, "price": price if type == "prod" else 0}
    update_tree(data)

def delete_from_tree(path):
    data = get_tree()
    parts = path.split(">")
    target = data
    for key in parts[:-1]: target = target["children"][key]
    if parts[-1] in target["children"]: del target["children"][parts[-1]]
    update_tree(data)

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 إدارة المتجر", callback_data="open_root")],
        [InlineKeyboardButton(text="👥 إدارة الخصومات", callback_data="manage_discounts")],
        [InlineKeyboardButton(text="📋 عرض الزبائن", callback_data="list_users")],
        [InlineKeyboardButton(text="📢 إرسال إعلان للكل", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="✉️ رسالة لشخص", callback_data="direct_msg")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👑 مرحباً بك في لوحة تحكم ALEX STORE:", reply_markup=get_main_kb())

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_broadcast)
    await call.message.edit_text("✍️ أرسل نص الإعلان:")

@dp.message(AdminStates.waiting_broadcast)
async def broadcast_exec(message: types.Message, state: FSMContext):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            for uid in f.read().splitlines():
                try: await bot.send_message(uid.strip(), message.text)
                except: continue
        await message.answer("✅ تم الإرسال.")
    await state.clear()

@dp.callback_query(F.data == "direct_msg")
async def direct_start(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_direct_id)
    await call.message.edit_text("🆔 آيدي الزبون:")

@dp.message(AdminStates.waiting_direct_id)
async def direct_id(message: types.Message, state: FSMContext):
    await state.update_data(target_id=message.text)
    await state.set_state(AdminStates.waiting_direct_text)
    await message.answer("✍️ أرسل نص الرسالة:")

@dp.message(AdminStates.waiting_direct_text)
async def direct_exec(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        await bot.send_message(data['target_id'], message.text)
        await message.answer("✅ تم الإرسال!")
    except: await message.answer("❌ خطأ في الآيدي.")
    await state.clear()

@dp.callback_query(F.data.startswith("open_"))
async def open_node(call: types.CallbackQuery):
    path = call.data.replace("open_", "")
    node = get_node_by_path(path)
    kb = []
    for name, item in node.get("children", {}).items():
        new_path = f"{path}>{name}" if path != "root" else name
        btn_text = f"📁 {name}" if item.get("type") == "folder" else f"🛒 {name} ({item.get('price', 0)}$)"
        kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"open_{new_path}"), 
                   InlineKeyboardButton(text="❌", callback_data=f"del_{new_path}")])
    kb.append([InlineKeyboardButton(text="➕ إضافة قسم", callback_data=f"addf_{path}"), 
               InlineKeyboardButton(text="➕ إضافة منتج", callback_data=f"addp_{path}")])
    back_data = "back_start"
    if path != "root":
        parent = ">".join(path.split(">")[:-1]) if ">" in path else "root"
        back_data = f"open_{parent}"
    kb.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=back_data)])
    await call.message.edit_text(f"📍 المسار: {path}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("del_"))
async def del_node(call: types.CallbackQuery):
    path = call.data.replace("del_", "")
    delete_from_tree(path)
    parent = ">".join(path.split(">")[:-1]) if ">" in path else "root"
    call.data = f"open_{parent}"
    await open_node(call)

@dp.callback_query(F.data.startswith(("addf_", "addp_")))
async def add_start(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split("_", 1)
    await state.update_data(path=parts[1], is_prod=parts[0] == "addp")
    await state.set_state(AdminStates.waiting_name)
    await call.message.edit_text("✍️ أرسل الاسم:")

@dp.message(AdminStates.waiting_name)
async def get_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data["is_prod"]:
        await state.update_data(name=message.text)
        await state.set_state(AdminStates.waiting_price)
        await message.answer("💰 أرسل السعر:")
    else:
        add_to_tree(data["path"], message.text, "folder")
        await message.answer("✅ تم.", reply_markup=get_main_kb())
        await state.clear()

@dp.message(AdminStates.waiting_price)
async def get_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    add_to_tree(data["path"], data["name"], "prod", message.text)
    await message.answer("✅ تم.", reply_markup=get_main_kb())
    await state.clear()

@dp.callback_query(F.data == "manage_discounts")
async def manage_discounts(call: types.CallbackQuery):
    discounts = load_json(DISCOUNTS_FILE, {})
    text = "👥 الخصومات:\n" + "\n".join([f"ID: {uid} | {val}%" for uid, val in discounts.items()])
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ إضافة خصم", callback_data="add_disc")], [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_start")]])
    await call.message.edit_text(text or "لا توجد خصومات.", reply_markup=kb)

@dp.callback_query(F.data == "add_disc")
async def add_disc_step1(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_user_id)
    await call.message.edit_text("🆔 آيدي الزبون:")

@dp.message(AdminStates.waiting_user_id)
async def add_disc_step2(message: types.Message, state: FSMContext):
    await state.update_data(target_uid=message.text)
    await state.set_state(AdminStates.waiting_discount)
    await message.answer("🔢 نسبة الخصم:")

@dp.message(AdminStates.waiting_discount)
async def add_disc_step3(message: types.Message, state: FSMContext):
    data = await state.get_data()
    discounts = load_json(DISCOUNTS_FILE, {})
    discounts[data['target_uid']] = message.text
    save_json(DISCOUNTS_FILE, discounts)
    await message.answer("✅ تم!", reply_markup=get_main_kb())
    await state.clear()

@dp.callback_query(F.data == "list_users")
async def list_users(call: types.CallbackQuery):
    if not os.path.exists(USERS_FILE):
        await call.message.edit_text("لا يوجد زبائن.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="back_start")]]))
        return
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    await call.message.edit_text(f"📋 الزبائن:\n" + "\n".join(users), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="back_start")]]))

@dp.callback_query(F.data == "back_start")
async def back_start(call: types.CallbackQuery):
    await call.message.edit_text("👑 لوحة تحكم ALEX STORE:", reply_markup=get_main_kb())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
