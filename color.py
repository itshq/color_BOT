#!/usr/bin/env python3

from datetime import datetime
import base64
import os
import re
import time
import requests
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# ==================== الإعدادات ====================
TOKEN = "8978043180:AAFwh_jmKITM3hYx9JgEMVbomZdmd43myZ0"
ADMIN_ID = 5011347901

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==================== البيانات ====================
users_data = {}
user_states = {}
total_colored = 0
PHOTO_URL = "https://e.top4top.io/p_3904sldur1.jpg"

# ==================== دالة موحدة لعرض القوائم بسلاسة بدون وميض ====================
def send_or_edit_menu(chat_id, message_id, caption, kb, is_navigation=False):
  if is_navigation:
    try:
      return bot.edit_message_caption(
          chat_id=chat_id,
          message_id=message_id,
          caption=caption,
          reply_markup=kb,
      )
    except:
      pass

  try:
    bot.delete_message(chat_id, message_id)
  except:
    pass

  try:
    return bot.send_photo(
        chat_id,
        PHOTO_URL,
        caption=caption,
        reply_markup=kb,
    )
  except:
    return bot.send_message(
        chat_id,
        caption,
        reply_markup=kb,
    )

def extract_all_strings_from_file(content):
  buttons_in_file = find_all_buttons(content)
  lines = content.split("\n")
  
  lines_to_skip = set()
  for btn in buttons_in_file:
    for idx in range(btn["start_line"], btn["end_line"]):
      lines_to_skip.add(idx)
      
  filtered_content = "\n".join([line for i, line in enumerate(lines) if i not in lines_to_skip])

  matches = re.findall(r'["\']([^"\n]{2,200})["\']', filtered_content)
  clean_strings = []

  ignored_terms = (
      "http://", "https://", "t.me/", "cb_", "style=", "primary", 
      "success", "danger", "InlineKeyboardButton", "callback_data", "url",
      "chat_id", "message_id", "parse_mode", "reply_markup", "waiting_",
      "action", "file_", "current_", "buttons", "content", "TOKEN", "ADMIN_ID",
      "PHOTO_URL", "users_data", "user_states", "text_modifications", "colored_buttons",
      "bot.", "def ", "import ", "from ", "return", "if ", "else:", "elif ",
      "try:", "except", "with ", "open(", "as ", "print(", "int(", "str(",
      ".py", "utf-8", "wb", "rb", "os.", "re.", "time."
  )

  for s in matches:
    s_clean = s.strip()
    if any(s_clean.startswith(term) or term in s_clean for term in ignored_terms):
      continue
    if ":" in s_clean and len(s_clean) > 15:
      continue
    if re.match(r'^[a-fA-F0-9]{15,}$', s_clean):
      continue
    if re.match(r'^[a-zA-Z_]+$', s_clean) and not " " in s_clean and len(s_clean) < 15:
      continue
    if len(s_clean) < 3:
      continue
    if s_clean not in clean_strings:
      clean_strings.append(s_clean)
        
  return clean_strings

def extract_button_text(button_code):
  all_strings = re.findall(r'["\']([^"\']+)["\']', button_code)
  for s in all_strings:
    s_clean = s.strip()
    if s_clean and not s_clean.startswith(("cb_", "http://", "https://", "t.me/", "callback_data", "url", "style", "primary", "success", "danger", "toggle_")):
      return s_clean
  return "زر بدون نص"

def extract_button_callback(button_code):
  match = re.search(r'callback_data\s*=\s*["\']([^"\']*)["\']', button_code)
  return match.group(1) if match else None

def extract_button_url(button_code):
  match = re.search(r'url\s*=\s*["\']([^"\']*)["\']', button_code)
  return match.group(1) if match else None

def add_style_to_button(button_code, style):
  if "style=" not in button_code:
    if button_code.rstrip().endswith(")"):
      return button_code[:-1] + f', style="{style}")'
    return button_code + f', style="{style}"'
  return re.sub(r'style="[^"]*"', f'style="{style}"', button_code)

def modify_button_text(button_code, new_text):
  if "text=" in button_code:
    return re.sub(r'text\s*=\s*["\'][^"\']*["\']', f'text="{new_text}"', button_code)
  else:
    match = re.search(r'InlineKeyboardButton\s*\(\s*["\'][^"\']*["\']', button_code)
    if match:
      return re.sub(r'InlineKeyboardButton\s*\(\s*["\'][^"\']*["\']', f'InlineKeyboardButton("{new_text}"', button_code, count=1)
  return button_code

def find_all_buttons(content):
  buttons = []
  lines = content.split("\n")
  i = 0
  while i < len(lines):
    line = lines[i]
    if "InlineKeyboardButton" in line and "(" in line:
      button_code = line
      j = i + 1
      open_par = line.count("(") - line.count(")")
      while open_par > 0 and j < len(lines):
        button_code += "\n" + lines[j]
        open_par += lines[j].count("(") - lines[j].count(")")
        j += 1

      buttons.append({
          "code": button_code,
          "text": extract_button_text(button_code),
          "callback_data": extract_button_callback(button_code),
          "url": extract_button_url(button_code),
          "start_line": i,
          "end_line": j,
      })
      i = j
    else:
      i += 1
  return buttons

def process_final_file(content, colored_dict, text_modifications):
  buttons = find_all_buttons(content)
  lines = content.split("\n")
  result_lines = lines.copy()
  all_indices = set(list(colored_dict.keys()) + list(text_modifications.keys()))
  
  for idx_str in all_indices:
    idx = int(idx_str)
    if idx < len(buttons):
      btn = buttons[idx]
      current_code = btn["code"]
      if idx_str in text_modifications:
        current_code = modify_button_text(current_code, text_modifications[idx_str])
      if idx_str in colored_dict:
        current_code = add_style_to_button(current_code, colored_dict[idx_str])
      result_lines[btn["start_line"] : btn["end_line"]] = current_code.split("\n")
  return "\n".join(result_lines)

def get_user(user_id, first_name="", username=""):
  uid = str(user_id)
  initial_points = 999999 if user_id == ADMIN_ID else 2

  if uid not in users_data:
    users_data[uid] = {
        "points": initial_points,
        "referrals": [],
        "colored_files": 0,
        "first_name": first_name,
        "username": username.lower() if username else "",
        "join_date": time.time(),
        "last_daily_claim": 0,
        "is_banned": False,
        "is_vip": True if user_id == ADMIN_ID else False,
        "quotes": [],
    }
    if user_id != ADMIN_ID:
      notify_admin(user_id, first_name, username)
  else:
    if username:
      users_data[uid]["username"] = username.lower()
    if "quotes" not in users_data[uid]:
      users_data[uid]["quotes"] = []

  if user_id == ADMIN_ID:
    users_data[uid]["points"] = 999999
    users_data[uid]["is_vip"] = True

  return users_data[uid]

def notify_admin(user_id, first_name, username):
  try:
    total = len(users_data)
    msg = (
        f"👤 <b>مستخدم جديد انضم للبوت!</b>\n\n┌ <b>الرقم الترتيبي:</b>"
        f" #{total}\n├ <b>الاسم:</b> {first_name}\n├ <b>الآيدي:</b>"
        f" <code>{user_id}</code>\n└ <b>المعرف:</b>"
        f" @{username if username else 'لا يوجد'}\n\n🕐 الوقت:"
        f" {datetime.now().strftime('%H:%M:%S')}"
    )
    bot.send_message(ADMIN_ID, msg)
  except:
    pass

def deduct_points(user_id, points):
  uid = str(user_id)
  if user_id == ADMIN_ID:
    return True
  if uid in users_data and users_data[uid]["points"] >= points:
    users_data[uid]["points"] -= points
    return True
  return False

def check_and_deduct_point(user_id, chat_id):
  user = get_user(user_id)
  if user_id == ADMIN_ID:
    return True
  if user["points"] < 1:
    bot.send_message(
        chat_id,
        "❌ <b>عذراً، نقاطك غير كافية!</b>\nتحتاج إلى نقطة واحدة (1) على الأقل لاستخدام هذه الميزة. قم بدعوة أصدقائك أو استخدم الهدية اليومية 🎁",
    )
    return False
  user["points"] -= 1
  return True

def get_referral_link(user_id):
  bot_info = bot.get_me()
  return f"https://t.me/{bot_info.username}?start=ref_{user_id}"

def get_main_keyboard(user_id):
  user = get_user(user_id)
  vip = "👑 VIP " if user.get("is_vip") else ""
  kb = InlineKeyboardMarkup(row_width=1)
  
  kb.add(InlineKeyboardButton("📢 إضافة اشتراك إجباري", callback_data="force_sub_menu", style="primary"))
  kb.add(InlineKeyboardButton("🎨 تلوين أزرار / إضافة إيموجيات", callback_data="color", style="primary"))
  kb.add(InlineKeyboardButton("🌐 فحص حالة البوتات", callback_data="check_bot_health", style="primary"))
  kb.add(InlineKeyboardButton("معالج الأخطاء 🔍", callback_data="check_errors", style="primary"))
  kb.add(InlineKeyboardButton("🔒 حماية وتشفير الكود", callback_data="obfuscate_menu", style="primary"))
  kb.add(InlineKeyboardButton("🧹 تنظيف وتحسين الكود", callback_data="format_menu", style="primary"))
  kb.add(InlineKeyboardButton("⚙️ تثبيت المكتبات", callback_data="libs_menu", style="primary"))
  
  kb.add(InlineKeyboardButton("🎁 الهدية اليومية", callback_data="daily_bonus", style="success"))
  kb.row(
      InlineKeyboardButton("💳 تحويل نقاط", callback_data="user_transfer_points_menu", style="success"),
      InlineKeyboardButton("💰 نقاطي", callback_data="points", style="success"),
  )
  kb.row(
      InlineKeyboardButton("🔗 رابط الدعوة", callback_data="referral", style="success"),
      InlineKeyboardButton("👥 قائمة الدعوات", callback_data="my_refs", style="success"),
  )
  kb.row(
      InlineKeyboardButton("ℹ️ طريقة الاستخدام", callback_data="howto", style="success"),
      InlineKeyboardButton("📜 سجل الملفات", callback_data="history", style="success"),
  )
  kb.add(InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/its_h_q", style="danger"))
  return kb, user["points"], vip

def get_color_menu(buttons_count):
  kb = InlineKeyboardMarkup(row_width=1)
  kb.row(InlineKeyboardButton("🎨 اختيار الأزرار يدوياً", callback_data="select_buttons", style="primary"))
  kb.row(InlineKeyboardButton("🔙 إلغاء والرجوع للقائمة", callback_data="back", style="danger"))
  return kb

def get_buttons_selection_menu(buttons_list, colored_dict=None, text_modifications=None, index=0):
  if colored_dict is None:
    colored_dict = {}
  if text_modifications is None:
    text_modifications = {}

  total_buttons = len(buttons_list)
  if index < 0:
    index = 0
  if index >= total_buttons:
    index = total_buttons - 1

  btn = buttons_list[index]
  raw_text = text_modifications.get(str(index), btn.get("text", f"زر {index + 1}"))
  btn_text = extract_button_text(raw_text) if "InlineKeyboard" in raw_text or not raw_text else raw_text
  
  kb = InlineKeyboardMarkup(row_width=1)
  display_text = f"{btn_text}"

  kb.add(InlineKeyboardButton(display_text, callback_data="ignore"))
  kb.add(InlineKeyboardButton("✨ إضافة إيموجي مميز", callback_data="add_special_emoji"))
  kb.add(InlineKeyboardButton("😊 إضافة إيموجي عادي", callback_data="add_normal_emoji"))
  kb.add(InlineKeyboardButton("🗑️ مسح الإيموجي", callback_data="remove_emoji"))
  kb.add(InlineKeyboardButton("✏️ تغير اسم الزر", callback_data="rename_button"))

  kb.row(
      InlineKeyboardButton("🔴 أحمر", callback_data=f"set_color_{index}_danger"),
      InlineKeyboardButton("🔵 أزرق", callback_data=f"set_color_{index}_primary"),
      InlineKeyboardButton("🟢 أخضر", callback_data=f"set_color_{index}_success"),
  )

  nav_row = []
  if index > 0:
    nav_row.append(InlineKeyboardButton("⬅️ الزر السابق", callback_data=f"select_page_{index - 1}"))
  if index < total_buttons - 1:
    nav_row.append(InlineKeyboardButton("الزر التالي ➡️", callback_data=f"select_page_{index + 1}"))

  if nav_row:
    kb.row(*nav_row)

  if len(colored_dict) > 0 or len(text_modifications) > 0:
    total_mod = len(set(list(colored_dict.keys()) + list(text_modifications.keys())))
    kb.row(InlineKeyboardButton(f"🎨 حفظ وتلوين ({total_mod} تعديل)", callback_data="confirm_custom_color"))

  kb.row(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_color"))
  return kb, total_buttons, len(colored_dict), index + 1, total_buttons

@bot.message_handler(commands=["start"])
def start_cmd(m):
  uid = m.from_user.id
  name = m.from_user.first_name
  user = m.from_user.username

  if len(m.text.split()) > 1:
    p = m.text.split()[1]
    if p.startswith("ref_"):
      rid = int(p.replace("ref_", ""))
      if rid != uid and str(rid) in users_data:
        users_data[str(rid)]["points"] += 1
        if uid not in users_data[str(rid)].get("referrals", []):
          users_data[str(rid)].setdefault("referrals", []).append(uid)
        try:
          bot.send_message(
              rid,
              "🎉 <b>مستخدم جديد انضم عبر رابط دعوتك!</b>\n\n➕ تم إضافة <b>1 نقطة</b> إلى رصيدك بنجاح.",
          )
        except:
          pass

  get_user(uid, name, user)
  kb, pts, vip = get_main_keyboard(uid)

  welcome_text = (
      "<blockquote><b>أهلاً بك في بوت تلوين أزرار تليجرام 🎨</b>\n\n"
      "ℹ️ <b>توضيح نظام النقاط:</b>\n"
      "• عند استخدام أي ميزة (إرسال ملف أو فحص توكن) سيتم خصم <b>نقطة واحدة (1)</b> فقط عند إتمام العملية بنجاح.\n"
      "• عند دعوة صديق عبر رابط الدعوة الخاص بك، ستربح <b>نقطة واحدة (1)</b>!\n"
      "• يمكنك أيضاً الحصول على نقاط مجانية يومياً عبر زر <b>الهدية اليومية 🎁</b>.</blockquote>"
  )

  try:
    bot.send_photo(
        m.chat.id,
        PHOTO_URL,
        caption=welcome_text,
        reply_markup=kb,
    )
  except:
    bot.send_message(
        m.chat.id,
        welcome_text,
        reply_markup=kb,
    )

@bot.callback_query_handler(
    func=lambda c: c.data
    in [
        "back",
        "points",
        "texts_menu",
        "add_quote",
        "referral",
        "my_refs",
        "history",
        "howto",
        "color",
        "check_errors",
        "user_transfer_points_menu",
        "user_transfer_specific",
        "user_transfer_all",
        "daily_bonus",
        "ignore",
        "add_special_emoji",
        "add_normal_emoji",
        "remove_emoji",
        "rename_button",
        "emoji_pos_left",
        "emoji_pos_right",
        "back_to_buttons_menu",
        "libs_menu",
        "auto_install_libs",
        "extract_libs",
        "obfuscate_menu",
        "format_menu",
        "check_bot_health",
        "force_sub_menu",
    ]
)
def simple_cb_handler(c):
  uid = c.from_user.id
  data = c.data

  if data == "ignore":
    bot.answer_callback_query(c.id)
    return

  # الانتقال لقسم الاشتراك الإجباري
  if data == "force_sub_menu":
    user_states[uid] = {"action": "waiting_force_sub_file"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="back", style="danger"))
    txt = (
        "<blockquote>📢 <b>قسم الاشتراك الإجباري:</b>\n\n"
        "💰 تكلفة العملية : 1 نقطة (عند إرسال الملف)\n\n"
        "📂 <b>أرسل لي ملف بايثون (.py) الخاص بك لإضافة نظام الاشتراك الإجباري إليه!</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  # الانتقال لقسم فحص التوكن
  if data == "check_bot_health":
    user_states[uid] = {"action": "waiting_bot_token"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="back", style="danger"))
    txt = (
        "<blockquote>🌐 <b>فحص حالة البوتات (Bot Health Checker):</b>\n\n"
        "💰 تكلفة العملية : 1 نقطة (عند إرسال التوكن)\n\n"
        "🤖 <b>أرسل لي توكن البوت (Bot Token) الذي تريد فحصه، وسأقوم بالتحقق مما إذا كان يعمل وجلب معلوماته الكاملة (الاسم، المعرف، الآيدي)!</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  # الانتقال لقسم تنظيف الكود
  if data == "format_menu":
    user_states[uid] = {"action": "waiting_format_file"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="back", style="danger"))
    txt = (
        "<blockquote>🧹 <b>قسم تنظيف وتحسين الكود (Formatter):</b>\n\n"
        "💰 تكلفة العملية : 1 نقطة (عند إرسال الملف)\n\n"
        "📂 <b>أرسل لي ملف بايثون (.py) وسأقوم بإزالة الأسطر الزائدة وتنظيم وترتيب الكود ليصبح احترافياً ومرتباً!</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  # الانتقال لقسم التشفير
  if data == "obfuscate_menu":
    user_states[uid] = {"action": "waiting_obfuscate_file"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="back", style="danger"))
    txt = (
        "<blockquote>🔒 <b>قسم حماية وتشفير ملفات البايثون:</b>\n\n"
        "💰 تكلفة العملية : 1 نقطة (عند إرسال الملف)\n\n"
        "📂 <b>أرسل لي ملف بايثون (.py) وسأقوم بتشفير محتواه وجعله صعب القراءة أو التعديل من قبل الآخرين (Obfuscation) مع الحفاظ على عمله بكفاءة!</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "libs_menu":
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("تثبيت المكتبات تلقائياً", callback_data="auto_install_libs", style="primary"))
    kb.add(InlineKeyboardButton("استخراج مكتبات الملف", callback_data="extract_libs", style="primary"))
    kb.add(InlineKeyboardButton("رجوع للقائمة الرئيسية", callback_data="back", style="danger"))
    
    txt = "<blockquote>⚙️ <b>قسم إدارة ومكتبات بايثون:</b>\n\nاختر العملية المطلوبة أدناه:</blockquote>"
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  # الانتقال للتثبيت التلقائي
  if data == "auto_install_libs":
    user_states[uid] = {"action": "waiting_auto_install_file"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="libs_menu", style="danger"))
    txt = (
        "<blockquote>📥 <b>تثبيت المكتبات تلقائياً:</b>\n\n"
        "💰 تكلفة العملية : 1 نقطة (عند إرسال الملف)\n\n"
        "📂 <b>أرسل لي ملف بايثون (.py) وسأقوم باستخراج المكتبات الخارجية المستوردة داخله وإضافتها كأوامر تثبيت (os.system('pip install ...')) بشكل آلي داخل الكود!</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  # الانتقال لاستخراج المكتبات
  if data == "extract_libs":
    user_states[uid] = {"action": "waiting_extract_libs_file"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="libs_menu", style="danger"))
    txt = (
        "<blockquote>📤 <b>استخراج مكتبات الملف:</b>\n\n"
        "💰 تكلفة العملية : 1 نقطة (عند إرسال الملف)\n\n"
        "📂 <b>أرسل لي ملف بايثون (.py) وسأقوم بقراءة الكود واستخراج كافة المكتبات المستخدمة فيه وإرسالها لك كملف متطلبات (requirements.txt)!</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "points":
    pts = "لانهائي ♾️" if uid == ADMIN_ID else get_user(uid)["points"]
    txt = "<blockquote>💰 <b>رصيدك الحالي:</b> <b>{}</b> نقطة.</blockquote>".format(pts)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back", style="danger"))
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  # الانتقال لمعالج الأخطاء
  if data == "check_errors":
    user_states[uid] = {"action": "waiting_error_check_file"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="back", style="danger"))
    txt = (
        "<blockquote>🔍 <b>قسم معالج الأخطاء لملفات البايثون:</b>\n\n"
        "💰 تكلفة العملية : 1 نقطة (عند إرسال الملف)\n\n"
        "📂 <b>أرسل لي ملف بايثون (.py) وسأقوم بفحصه برمجياً للتأكد من خلوه من أخطاء الـ Syntax أو الأقواس!</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "referral":
    link = get_referral_link(uid)
    refs_count = len(users_data.get(str(uid), {}).get("referrals", []))
    txt = (
        "<blockquote>🔗 <b>مرحباً بك في قسم دعوة الأصدقاء</b>\n\n"
        "• لكل شخص يدخل عبر رابطك ستحصل على <b>1 نقطة</b>.\n"
        f"• عدد الأشخاص الذين دعوتهم: <b>{refs_count}</b> شخص\n\n"
        f"<b>رابط الدعوة الخاص بك:</b>\n<code>{link}</code></blockquote>"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back", style="danger"))
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "my_refs":
    user_info = get_user(uid)
    refs = user_info.get("referrals", [])
    txt = (
        "<blockquote>👥 <b>قائمة الأشخاص الذين دعوتهم:</b>\n\n"
        f"• الإجمالي: <b>{len(refs)}</b> أعضاء.</blockquote>"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back", style="danger"))
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "history":
    user_info = get_user(uid)
    colored_count = user_info.get("colored_files", 0)
    txt = (
        "<blockquote>📜 <b>سجل استخدامك للبوت:</b>\n\n"
        f"🎨 عدد الملفات الملونة: <b>{colored_count}</b> ملف.</blockquote>"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back", style="danger"))
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "howto":
    txt = (
        "<blockquote>ℹ️ <b>طريقة استخدام بوت تلوين الأزرار:</b>\n\n"
        "1️⃣ اختر أي ميزة من القائمة الرئيسية (تكلفة العملية : 1 نقطة عند إرسال الملف أو التوكن).\n"
        "2️⃣ أرسل ملف بايثون بصيغة <code>.py</code> أو التوكن المطلوب.\n"
        "3️⃣ احصل على النتيجة فوراً بسلاسة تامة!</blockquote>"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back", style="danger"))
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "user_transfer_points_menu":
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("تحويل لشخص معين", callback_data="user_transfer_specific", style="success"))
    kb.add(InlineKeyboardButton("تحويل نقاط لجميع", callback_data="user_transfer_all", style="success"))
    kb.add(InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back", style="danger"))
    
    txt = "<blockquote>💳 <b>قسم تحويل النقاط:</b>\n\nاختر طريقة التحويل المناسبة لك:</blockquote>"
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "user_transfer_specific":
    user_states[uid] = {"action": "waiting_transfer_user"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="user_transfer_points_menu", style="danger"))
    txt = (
        "<blockquote>📤 <b>أرسل الآن (آيدي الشخص أو معرفه @username) مع عدد النقاط المراد تحويلها بالشكل التالي:</b>\n\n"
        "<code>ID NUM</code> أو <code>@username NUM</code>\n"
        "مثال: <code>5011347901 5</code></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.register_next_step_handler(c.message, process_transfer_specific)
    bot.answer_callback_query(c.id)
    return

  if data == "user_transfer_all" and uid == ADMIN_ID:
    user_states[uid] = {"action": "waiting_transfer_all"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="user_transfer_points_menu", style="danger"))
    txt = (
        "<blockquote>📢 <b>أرسل عدد النقاط التي تريد إضافتها لجميع مستخدمي البوت:</b>\n"
        "مثال: <code>10</code></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.register_next_step_handler(c.message, process_transfer_all)
    bot.answer_callback_query(c.id)
    return

  if data == "rename_button":
    if uid in user_states:
      user_states[uid]["action"] = "waiting_new_button_name"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_buttons_menu", style="danger"))
    txt = (
        "<blockquote>✏️ <b>تغيير اسم الزر:</b>\n\n"
        "💬 <b>أرسل الاسم الجديد الذي تريده لهذا الزر الآن:</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.register_next_step_handler(c.message, process_rename_button_input)
    bot.answer_callback_query(c.id)
    return

  if data == "add_special_emoji":
    if uid in user_states:
      user_states[uid]["emoji_type"] = "special"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(
        InlineKeyboardButton("◀️ جهة اليسار", callback_data="emoji_pos_left", style="primary"),
        InlineKeyboardButton("جهة اليمين ▶️", callback_data="emoji_pos_right", style="primary"),
    )
    kb.row(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_buttons_menu", style="danger"))
    send_or_edit_menu(c.message.chat.id, c.message.message_id, "<blockquote>✨ <b>اختر مكان وضع الإيموجي المميز بالنسبة لنص الزر:</b></blockquote>", kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "add_normal_emoji":
    if uid in user_states:
      user_states[uid]["emoji_type"] = "normal"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.row(
        InlineKeyboardButton("◀️ جهة اليسار", callback_data="emoji_pos_left", style="primary"),
        InlineKeyboardButton("جهة اليمين ▶️", callback_data="emoji_pos_right", style="primary"),
    )
    kb.row(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_buttons_menu", style="danger"))
    send_or_edit_menu(c.message.chat.id, c.message.message_id, "<blockquote>😊 <b>اختر مكان وضع الإيموجي العادي بالنسبة لنص الزر:</b></blockquote>", kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data in ["emoji_pos_left", "emoji_pos_right"]:
    pos = "left" if data == "emoji_pos_left" else "right"
    if uid in user_states:
      user_states[uid]["emoji_position"] = pos
      user_states[uid]["action"] = "waiting_emoji_input"
    
    pos_name = "اليسار ◀️" if pos == "left" else "اليمين ▶️"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_buttons_menu", style="danger"))
    txt = (
        f"<blockquote>🎯 تم اختيار الوضع: <b>{pos_name}</b>\n\n"
        "💬 <b>الآن أرسل الإيموجي الذي تريد إضافته:</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.register_next_step_handler(c.message, process_emoji_input)
    bot.answer_callback_query(c.id)
    return

  if data == "back_to_buttons_menu":
    if uid in user_states:
      state = user_states[uid]
      state["action"] = "selecting_buttons"
      buttons_list = state.get("buttons", [])
      colored_dict = state.get("colored_buttons", {})
      text_mods = state.get("text_modifications", {})
      index = state.get("current_page", 0)
      kb, total_btns, colored_count, current_idx, total_pages = (
          get_buttons_selection_menu(buttons_list, colored_dict, text_mods, index)
      )
      total_mod = len(set(list(colored_dict.keys()) + list(text_mods.keys())))
      txt = (
          "<blockquote>🎨 <b>اختر اللون المناسب لكل زر يدوياً:</b>\n\n📊 إجمالي الأزرار:"
          f" <b>{total_btns}</b>\n🎨 الأزرار المعدلة:"
          f" <b>{total_mod}</b>\n📍 الزر الحالي:"
          f" <b>{current_idx} من {total_pages}</b></blockquote>"
      )
      send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if data == "remove_emoji":
    if uid in user_states and "buttons" in user_states[uid]:
      state = user_states[uid]
      index = state.get("current_page", 0)
      buttons_list = state.get("buttons", [])
      if index < len(buttons_list):
        btn = buttons_list[index]
        text_mods = state.setdefault("text_modifications", {})
        current_text = text_mods.get(str(index), btn.get("text", ""))
        emoji_pattern = re.compile(
            r"["
            r"\U0001f300-\U0001f5ff"
            r"\U0001f600-\U0001f64f"
            r"\U0001f680-\U0001f6ff"
            r"\U0001f700-\U0001f77f"
            r"\U0001f780-\U0001f7ff"
            r"\U0001f800-\U0001f8ff"
            r"\U0001f900-\U0001f9ff"
            r"\U0001fa00-\U0001fa6f"
            r"\U0001fa70-\U0001faff"
            r"\u2600-\u26ff"
            r"\u2700-\u27bf"
            r"]+", flags=re.UNICODE
        )
        new_text = emoji_pattern.sub("", current_text).strip()
        text_mods[str(index)] = new_text
        user_states[uid] = state
        
        colored_dict = state.get("colored_buttons", {})
        kb, total_btns, colored_count, current_idx, total_pages = (
            get_buttons_selection_menu(buttons_list, colored_dict, text_mods, index)
        )
        total_mod = len(set(list(colored_dict.keys()) + list(text_mods.keys())))
        txt = (
            "<blockquote>🎨 <b>اختر اللون المناسب لكل زر يدوياً:</b>\n\n📊 إجمالي الأزرار:"
            f" <b>{total_btns}</b>\n🎨 الأزرار المعدلة:"
            f" <b>{total_mod}</b>\n📍 الزر الحالي:"
            f" <b>{current_idx} من {total_pages}</b></blockquote>"
        )
        try:
          bot.edit_message_caption(
              chat_id=c.message.chat.id,
              message_id=c.message.message_id,
              caption=txt,
              reply_markup=kb
          )
        except Exception:
          pass
        bot.answer_callback_query(c.id, "🗑️ تم مسح الإيموجي من الزر بنجاح!", True)
        return
    bot.answer_callback_query(c.id, "❌ حدث خطأ، يرجى إعادة المحاولة.")
    return

  if data == "back":
    try:
      kb, pts, vip = get_main_keyboard(uid)
      welcome_text = (
          "<blockquote><b>أهلاً بك في بوت تلوين أزرار تليجرام 🎨</b>\n\n"
          "ℹ️ <b>توضيح نظام النقاط:</b>\n"
          "• عند استخدام أي ميزة (إرسال ملف أو فحص توكن) سيتم خصم <b>نقطة واحدة (1)</b> فقط عند إتمام العملية بنجاح.\n"
          "• عند دعوة صديق عبر رابط الدعوة الخاص بك، ستربح <b>نقطة واحدة (1)</b>!\n"
          "• يمكنك أيضاً الحصول على نقاط مجانية يومياً عبر زر <b>الهدية اليومية 🎁</b>.</blockquote>"
      )
      send_or_edit_menu(
          c.message.chat.id,
          c.message.message_id,
          welcome_text,
          kb,
          is_navigation=True
      )
    except:
      pass
    bot.answer_callback_query(c.id)
    return

  if data == "daily_bonus":
    uid_str = str(uid)
    current_time = time.time()
    last_claim = users_data[uid_str].get("last_daily_claim", 0)
    cooldown = 86400

    if current_time - last_claim < cooldown:
      remaining_time = int(cooldown - (current_time - last_claim))
      hours = remaining_time // 3600
      minutes = (remaining_time % 3600) // 60
      bot.answer_callback_query(
          c.id,
          f"⏳ عذراً، لقد استلمت هديتك اليومية مسبقاً.\nيرجى الانتظار {hours} ساعة و {minutes} دقيقة.",
          show_alert=True,
      )
      return

    users_data[uid_str]["last_daily_claim"] = current_time
    users_data[uid_str]["points"] += 1
    bot.answer_callback_query(c.id, "🎉 مبروك! حصلت على نقطة الهدية اليومية بنجاح 🎁", show_alert=True)
    return

  # الانتقال لقسم التلوين
  if data == "color":
    current_user = get_user(uid)
    user_states[uid] = {"action": "waiting_file"}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 إلغاء", callback_data="back", style="danger"))

    text_content = (
        "<blockquote>🎨 <b>قسم تلوين ملفات البايثون</b>\n\n"
        f"💰 تكلفة العملية : 1 نقطة\n"
        "📊 نقاطك الحالية:"
        f" <b>{'لانهائي ♾️' if uid == ADMIN_ID else current_user['points']}</b> نقطة\n\n"
        "📤 <b>الرجاء إرسال ملف بايثون بصيغة (.py) الآن:</b>\n⚠️ تنبيه: أقصى حجم مسموح للملف هو 1MB.</blockquote>"
    )

    send_or_edit_menu(c.message.chat.id, c.message.message_id, text_content, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

def process_transfer_specific(m):
  uid = m.from_user.id
  if uid not in user_states:
    return
  text = m.text.strip()
  parts = text.split()
  if len(parts) < 2:
    bot.reply_to(m, "❌ الصياغة غير صحيحة. يرجى إرسال الآيدي أو اليوزر مع العدد بالشكل الصحيح.")
    return
  target_str = parts[0]
  try:
    amount = int(parts[1])
  except ValueError:
    bot.reply_to(m, "❌ عدد النقاط يجب أن يكون رقماً صحيحاً.")
    return

  if amount <= 0:
    bot.reply_to(m, "❌ يرجى إدخال عدد نقاط أكبر من الصفر.")
    return

  sender_data = get_user(uid)
  if sender_data["points"] < amount and uid != ADMIN_ID:
    bot.reply_to(m, f"❌ عذراً، لا تمتلك نقاط كافية! رصيدك الحالي: {sender_data['points']}")
    return

  target_uid = None
  if target_str.isdigit():
    target_uid = target_str
  elif target_str.startswith("@"):
    uname_clean = target_str.replace("@", "").lower()
    for u_id, u_info in users_data.items():
      if u_info.get("username") == uname_clean:
        target_uid = u_id
        break

  if not target_uid or target_uid not in users_data:
    bot.reply_to(m, "❌ لم يتم العثور على المستخدم في قاعدة بيانات البوت.")
    return

  if str(target_uid) == str(uid):
    bot.reply_to(m, "❌ لا يمكنك تحويل نقاط لنفسك!")
    return

  if uid != ADMIN_ID:
    sender_data["points"] -= amount

  users_data[str(target_uid)]["points"] += amount
  bot.reply_to(m, f"✅ تم تحويل <b>{amount} نقطة</b> بنجاح إلى المستخدم!")
  try:
    bot.send_message(int(target_uid), f"🎁 <b>وصلتك هدية / تحويل نقاط!</b>\n\n➕ تم إضافة <b>{amount} نقطة</b> إلى رصيدك.")
  except:
    pass
  if uid in user_states:
    del user_states[uid]

def process_transfer_all(m):
  uid = m.from_user.id
  if uid != ADMIN_ID:
    bot.reply_to(m, "❌ عذراً، هذا الأمر مخصص للمطور فقط.")
    if uid in user_states:
      del user_states[uid]
    return
  try:
    amount = int(m.text.strip())
  except ValueError:
    bot.reply_to(m, "❌ يرجى إرسال رقم صحيح.")
    return

  if amount <= 0:
    bot.reply_to(m, "❌ يجب أن يكون العدد أكبر من صفر.")
    return

  count = 0
  for u_id in users_data:
    users_data[u_id]["points"] += amount
    count += 1
    try:
      bot.send_message(int(u_id), f"📢 <b>تنبيه من المطور:</b>\n\n🎁 تم إضافة <b>{amount} نقطة</b> إلى رصيدك!")
    except:
      pass

  bot.reply_to(m, f"✅ تم إضافة <b>{amount} نقطة</b> إلى جميع المستخدمين ({count} مستخدم) بنجاح.")
  if uid in user_states:
    del user_states[uid]

def process_rename_button_input(m):
  uid = m.from_user.id
  if uid not in user_states:
    return

  state = user_states[uid]
  new_name = m.text.strip()
  index = state.get("current_page", 0)
  buttons_list = state.get("buttons", [])

  try:
    bot.delete_message(m.chat.id, m.message_id)
  except:
    pass

  if index < len(buttons_list):
    text_mods = state.setdefault("text_modifications", {})
    text_mods[str(index)] = new_name
    state["action"] = "selecting_buttons"
    user_states[uid] = state

    colored_dict = state.get("colored_buttons", {})
    kb, total_btns, colored_count, current_idx, total_pages = (
        get_buttons_selection_menu(buttons_list, colored_dict, text_mods, index)
    )
    total_mod = len(set(list(colored_dict.keys()) + list(text_mods.keys())))
    txt = (
        "<blockquote>🎨 <b>اختر اللون المناسب لكل زر يدوياً:</b>\n\n📊 إجمالي الأزرار:"
        f" <b>{total_btns}</b>\n🎨 الأزرار المعدلة:"
        f" <b>{total_mod}</b>\n📍 الزر الحالي:"
        f" <b>{current_idx} من {total_pages}</b></blockquote>"
    )
    
    try:
      bot.send_photo(
          chat_id=m.chat.id,
          photo=PHOTO_URL,
          caption=txt,
          reply_markup=kb
      )
    except Exception:
      try:
        bot.send_message(
            chat_id=m.chat.id,
            text=txt,
            reply_markup=kb
        )
      except:
        pass

def process_emoji_input(m):
  uid = m.from_user.id
  if uid not in user_states:
    return

  state = user_states[uid]
  emoji = m.text.strip()
  position = state.get("emoji_position", "right")
  index = state.get("current_page", 0)
  buttons_list = state.get("buttons", [])

  try:
    bot.delete_message(m.chat.id, m.message_id)
  except:
    pass

  if index < len(buttons_list):
    btn = buttons_list[index]
    text_mods = state.setdefault("text_modifications", {})
    current_text = text_mods.get(str(index), btn.get("text", ""))

    emoji_pattern = re.compile(
        r"["
        r"\U0001f300-\U0001f5ff"
        r"\U0001f600-\U0001f64f"
        r"\U0001f680-\U0001f6ff"
        r"\U0001f700-\U0001f77f"
        r"\U0001f780-\U0001f7ff"
        r"\U0001f800-\U0001f8ff"
        r"\U0001f900-\U0001f9ff"
        r"\U0001fa00-\U0001fa6f"
        r"\U0001fa70-\U0001faff"
        r"\u2600-\u26ff"
        r"\u2700-\u27bf"
        r"]+", flags=re.UNICODE
    )
    clean_text = emoji_pattern.sub("", current_text).strip()
    
    if position == "right":
      new_text = f"{emoji} {clean_text}"
    else:
      new_text = f"{clean_text} {emoji}"

    text_mods[str(index)] = new_text
    state["action"] = "selecting_buttons"
    user_states[uid] = state

    colored_dict = state.get("colored_buttons", {})
    kb, total_btns, colored_count, current_idx, total_pages = (
        get_buttons_selection_menu(buttons_list, colored_dict, text_mods, index)
    )
    total_mod = len(set(list(colored_dict.keys()) + list(text_mods.keys())))
    txt = (
        "<blockquote>🎨 <b>اختر اللون المناسب لكل زر يدوياً:</b>\n\n📊 إجمالي الأزرار:"
        f" <b>{total_btns}</b>\n🎨 الأزرار المعدلة:"
        f" <b>{total_mod}</b>\n📍 الزر الحالي:"
        f" <b>{current_idx} من {total_pages}</b></blockquote>"
    )
    
    try:
      bot.send_photo(
          chat_id=m.chat.id,
          photo=PHOTO_URL,
          caption=txt,
          reply_markup=kb
      )
    except Exception:
      try:
        bot.send_message(
            chat_id=m.chat.id,
            text=txt,
            reply_markup=kb
        )
      except:
        pass

@bot.message_handler(content_types=["text"])
def handle_text_messages(m):
  uid = m.from_user.id
  if uid not in user_states:
    return

  state = user_states[uid]
  action = state.get("action")

  if action == "waiting_force_sub_channels":
    text = m.text.strip()
    if text == "تم الانتهاء":
      channels = state.get("channels", [])
      if not channels:
        bot.reply_to(m, "❌ لم تقم بإرسال أي قناة أو مجموعة! يرجى إرسالها أو الضغط على زر الإلغاء.")
        return
      
      file_content = state.get("file_content")
      try:
        original = file_content.decode("utf-8")
      except:
        original = file_content

      channels_repr = repr(channels)
      force_sub_snippet = f"""
# ==================== نظام الاشتراك الإجباري ====================
FORCE_CHANNELS = {channels_repr}

def check_sub(bot_inst, user_id):
    for ch in FORCE_CHANNELS:
        try:
            res = bot_inst.get_chat_member(ch, user_id)
            if res.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

@bot.message_handler(commands=['start'])
def force_sub_start_wrapper(message):
    if not check_sub(bot, message.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        for idx, ch in enumerate(FORCE_CHANNELS):
            kb.add(InlineKeyboardButton(f"اشتراك في القناة {{idx+1}}", url=f"https://t.me/{{ch.replace('@','')}}"))
        kb.add(InlineKeyboardButton("✅ اشتركت، تحقق", callback_data="check_force_sub"))
        bot.send_message(message.chat.id, "❌ <b>عذراً، يجب عليك الاشتراك في القنوات أدناه لاستخدام البوت!</b>", reply_markup=kb)
        return
"""
      updated_content = force_sub_snippet + "\n\n" + original
      
      timestamp = int(time.time())
      filename = f"forcesub_{timestamp}_bot.py"
      with open(filename, "wb") as f:
        f.write(updated_content.encode("utf-8"))

      with open(filename, "rb") as f:
        bot.send_document(m.chat.id, f, caption="✅ <b>تم إضافة نظام الاشتراك الإجباري إلى ملفك بنجاح تام!</b>\n💰 تكلفة العملية : 1 نقطة")
      os.remove(filename)
      del user_states[uid]
      return
    else:
      lines = text.split("\n")
      channels = state.setdefault("channels", [])
      for line in lines:
        clean_ch = line.strip()
        if clean_ch:
          if clean_ch.startswith("https://t.me/"):
            clean_ch = "@" + clean_ch.split("/")[-1]
          elif not clean_ch.startswith("@") and not clean_ch.startswith("-100"):
            clean_ch = "@" + clean_ch
          if clean_ch not in channels:
            channels.append(clean_ch)
      
      msg_text = (
          f"<blockquote>✅ <b>تمت إضافة القنوات/المجموعات بنجاح.</b>\n\n"
          f"📋 <b>القنوات الحالية المسجلة:</b> <code>{len(channels)}</code>\n\n"
          f"👉 أرسل المزيد أو اضغط على زر <b>تم الانتهاء</b> أدناه عند الانتهاء.</blockquote>"
      )
      bot.reply_to(m, msg_text)
      return

  if action == "waiting_bot_token":
    # خصم النقطة عند إرسال وفحص التوكن فعلياً
    if not check_and_deduct_point(uid, m.chat.id):
      del user_states[uid]
      return

    token = m.text.strip()
    wait = bot.reply_to(m, "⏳ <b>جاري فحص حالة البوت والتحقق من التوكن...</b>")
    try:
      url = f"https://api.telegram.org/bot{token}/getMe"
      response = requests.get(url, timeout=10)
      res_json = response.json()

      kb = InlineKeyboardMarkup()
      kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back", style="danger"))

      if res_json.get("ok"):
        bot_info = res_json["result"]
        bot_name = bot_info.get("first_name", "غير معروف")
        bot_username = bot_info.get("username", "لا يوجد")
        bot_id = bot_info.get("id", "غير معروف")

        txt = (
            "✅ <b>البوت يعمل بكفاءة وأونلاين تماماً! (Online)</b>\n\n"
            f"👤 <b>اسم البوت:</b> {bot_name}\n"
            f"🔗 <b>المعرف:</b> @{bot_username}\n"
            f"🆔 <b>الآيدي:</b> <code>{bot_id}</code>\n"
            f"🤖 <b>نوع الحساب:</b> بوت رسمي تليجرام\n\n"
            "💰 تكلفة العملية : 1 نقطة"
        )
        bot.edit_message_text(chat_id=m.chat.id, message_id=wait.message_id, text=txt, reply_markup=kb)
      else:
        err_desc = res_json.get("description", "التوكن غير صالح")
        txt = f"❌ <b>فشل فحص البوت!</b>\n\n<b>السبب:</b> <code>{err_desc}</code>\nتأكد من صحة التوكن وأنه صحيح."
        bot.edit_message_text(chat_id=m.chat.id, message_id=wait.message_id, text=txt, reply_markup=kb)
    except Exception as e:
      kb = InlineKeyboardMarkup()
      kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back", style="danger"))
      bot.edit_message_text(chat_id=m.chat.id, message_id=wait.message_id, text=f"❌ حدث خطأ أثناء الاتصال بالبورد: <code>{str(e)[:150]}</code>", reply_markup=kb)
    del user_states[uid]
    return

@bot.message_handler(content_types=["document", "photo"])
def handle_file(m):
  uid = m.from_user.id
  current_user = get_user(uid)

  if uid not in user_states:
    bot.reply_to(m, "❌ يرجى اختيار القسم المطلوب من القائمة الرئيسية أولاً!")
    return

  state = user_states[uid]
  action = state.get("action")

  if action == "waiting_force_sub_file":
    if m.content_type != "document" or not m.document.file_name.endswith(".py"):
      bot.reply_to(m, "❌ يرجى إرسال ملف بايثون بصيغة <code>.py</code> حصراً!")
      return

    # خصم النقطة عند إرسال الملف وقبوله
    if not check_and_deduct_point(uid, m.chat.id):
      del user_states[uid]
      return

    try:
      file_info = bot.get_file(m.document.file_id)
      downloaded = bot.download_file(file_info.file_path)
      
      user_states[uid] = {
          "action": "waiting_force_sub_channels",
          "file_content": downloaded,
          "channels": []
      }
      
      kb = InlineKeyboardMarkup()
      kb.add(InlineKeyboardButton("✅ تم الانتهاء", callback_data="finish_force_sub", style="primary"))
      kb.add(InlineKeyboardButton("🔙 إلغاء", callback_data="back", style="danger"))
      
      bot.reply_to(
          m,
          "<blockquote>📂 <b>تم استلام الملف بنجاح!</b>\n\n"
          "💰 تكلفة العملية : 1 نقطة\n\n"
          "💬 <b>الآن أرسل روابط أو معرفات القنوات أو المجموعات (كل قناة في سطر أو دفعة واحدة).\n"
          "مثال:\n@Channel_Name\nhttps://t.me/ChannelName\n\nعند الانتهاء اضغط على زر 'تم الانتهاء' أدناه:</b></blockquote>",
          reply_markup=kb
      )
    except Exception as e:
      bot.reply_to(m, f"❌ حدث خطأ: <code>{str(e)[:150]}</code>")
      del user_states[uid]
    return

  if action == "waiting_format_file":
    if m.content_type != "document" or not m.document.file_name.endswith(".py"):
      bot.reply_to(m, "❌ يرجى إرسال ملف بايثون بصيغة <code>.py</code> حصراً!")
      return

    if not check_and_deduct_point(uid, m.chat.id):
      del user_states[uid]
      return

    wait = bot.reply_to(m, "⏳ <b>جاري تنظيف وتنسيق الكود البرمجي...</b>")
    try:
      file_info = bot.get_file(m.document.file_id)
      downloaded = bot.download_file(file_info.file_path)
      content_str = downloaded.decode("utf-8") if isinstance(downloaded, bytes) else downloaded

      lines = content_str.split("\n")
      cleaned_lines = []
      empty_count = 0
      for line in lines:
        if line.strip() == "":
          empty_count += 1
          if empty_count <= 2:
            cleaned_lines.append("")
        else:
          empty_count = 0
          cleaned_lines.append(line.rstrip())

      formatted_code = "\n".join(cleaned_lines)

      timestamp = int(time.time())
      filename = f"formatted_{timestamp}_{m.document.file_name}"
      with open(filename, "wb") as f:
        f.write(formatted_code.encode("utf-8"))

      with open(filename, "rb") as f:
        bot.send_document(m.chat.id, f, caption="✅ <b>تم تنظيف وتحسين الكود البرمجي بنجاح!</b>\n💰 تكلفة العملية : 1 نقطة")
      os.remove(filename)
      bot.delete_message(m.chat.id, wait.message_id)
    except Exception as e:
      bot.edit_message_text(chat_id=m.chat.id, message_id=wait.message_id, text=f"❌ حدث خطأ أثناء التنسيق: <code>{str(e)[:150]}</code>")
    del user_states[uid]
    return

  if action == "waiting_obfuscate_file":
    if m.content_type != "document" or not m.document.file_name.endswith(".py"):
      bot.reply_to(m, "❌ يرجى إرسال ملف بايثون بصيغة <code>.py</code> حصراً!")
      return

    if not check_and_deduct_point(uid, m.chat.id):
      del user_states[uid]
      return

    wait = bot.reply_to(m, "⏳ <b>جاري تشفير وحماية الكود البرمجي...</b>")
    try:
      file_info = bot.get_file(m.document.file_id)
      downloaded = bot.download_file(file_info.file_path)
      content_str = downloaded.decode("utf-8") if isinstance(downloaded, bytes) else downloaded

      encoded_bytes = base64.b64encode(content_str.encode("utf-8"))
      encoded_str = encoded_bytes.decode("utf-8")

      obfuscated_code = (
          "# -*- coding: utf-8 -*-\n"
          "# 🔒 Protected by Bot Security System\n"
          "import base64\n"
          f"exec(base64.b64decode('{encoded_str}').decode('utf-8'))\n"
      )

      timestamp = int(time.time())
      filename = f"protected_{timestamp}_{m.document.file_name}"
      with open(filename, "wb") as f:
        f.write(obfuscated_code.encode("utf-8"))

      with open(filename, "rb") as f:
        bot.send_document(m.chat.id, f, caption="✅ <b>تم تشفير وحماية الملف بنجاح!</b>\n💰 تكلفة العملية : 1 نقطة")
      os.remove(filename)
      bot.delete_message(m.chat.id, wait.message_id)
    except Exception as e:
      bot.edit_message_text(chat_id=m.chat.id, message_id=wait.message_id, text=f"❌ حدث خطأ أثناء التشفير: <code>{str(e)[:150]}</code>")
    del user_states[uid]
    return

  if action == "waiting_auto_install_file":
    if m.content_type != "document" or not m.document.file_name.endswith(".py"):
      bot.reply_to(m, "❌ يرجى إرسال ملف بايثون بصيغة <code>.py</code> حصراً!")
      return

    if not check_and_deduct_point(uid, m.chat.id):
      del user_states[uid]
      return

    wait = bot.reply_to(m, "⏳ <b>جاري تحليل الكود وإضافة أوامر التثبيت التلقائي للمكتبات...</b>")
    try:
      file_info = bot.get_file(m.document.file_id)
      downloaded = bot.download_file(file_info.file_path)
      content_str = downloaded.decode("utf-8") if isinstance(downloaded, bytes) else downloaded

      imported_modules = set()
      for line in content_str.split("\n"):
        line_stripped = line.strip()
        if line_stripped.startswith("import "):
          mods = line_stripped.replace("import ", "").split(",")
          for mod in mods:
            imported_modules.add(mod.strip().split()[0].split(".")[0])
        elif line_stripped.startswith("from "):
          parts = line_stripped.split()
          if len(parts) > 1:
            imported_modules.add(parts[1].split(".")[0])

      builtin_libs = {
          "os", "sys", "re", "math", "time", "datetime", "json", "random", 
          "urllib", "collections", "itertools", "functools", "pathlib", 
          "subprocess", "threading", "logging", "io", "string"
      }
      external_libs = [lib for lib in imported_modules if lib not in builtin_libs and lib.isidentifier()]

      if external_libs:
        install_snippet = "\n".join([f"import os\ntry:\n    import {lib}\nexcept ImportError:\n    os.system('pip install {lib}')" for lib in external_libs])
        updated_content = install_snippet + "\n\n" + content_str
      else:
        updated_content = content_str

      timestamp = int(time.time())
      filename = f"auto_libs_{timestamp}_{m.document.file_name}"
      with open(filename, "wb") as f:
        f.write(updated_content.encode("utf-8"))

      with open(filename, "rb") as f:
        bot.send_document(m.chat.id, f, caption="✅ <b>تم تعديل الملف وإضافة آلية تثبيت المكتبات الخارجية تلقائياً!</b>\n💰 تكلفة العملية : 1 نقطة")
      os.remove(filename)
      bot.delete_message(m.chat.id, wait.message_id)
    except Exception as e:
      bot.edit_message_text(chat_id=m.chat.id, message_id=wait.message_id, text=f"❌ حدث خطأ: <code>{str(e)[:150]}</code>")
    del user_states[uid]
    return

  if action == "waiting_extract_libs_file":
    if m.content_type != "document" or not m.document.file_name.endswith(".py"):
      bot.reply_to(m, "❌ يرجى إرسال ملف بايثون بصيغة <code>.py</code> حصراً!")
      return

    if not check_and_deduct_point(uid, m.chat.id):
      del user_states[uid]
      return

    wait = bot.reply_to(m, "⏳ <b>جاري قراءة الملف واستخراج المكتبات...</b>")
    try:
      file_info = bot.get_file(m.document.file_id)
      downloaded = bot.download_file(file_info.file_path)
      content_str = downloaded.decode("utf-8") if isinstance(downloaded, bytes) else downloaded

      imported_modules = set()
      for line in content_str.split("\n"):
        line_stripped = line.strip()
        if line_stripped.startswith("import "):
          mods = line_stripped.replace("import ", "").split(",")
          for mod in mods:
            imported_modules.add(mod.strip().split()[0].split(".")[0])
        elif line_stripped.startswith("from "):
          parts = line_stripped.split()
          if len(parts) > 1:
            imported_modules.add(parts[1].split(".")[0])

      builtin_libs = {
          "os", "sys", "re", "math", "time", "datetime", "json", "random", 
          "urllib", "collections", "itertools", "functools", "pathlib", 
          "subprocess", "threading", "logging", "io", "string"
      }
      external_libs = [lib for lib in imported_modules if lib not in builtin_libs and lib.isidentifier()]

      req_text = "\n".join(external_libs)
      req_filename = "requirements.txt"
      with open(req_filename, "w", encoding="utf-8") as f:
        f.write(req_text)

      with open(req_filename, "rb") as f:
        bot.send_document(m.chat.id, f, caption="✅ <b>تم استخراج مكتبات الملف بنجاح!</b>\n💰 تكلفة العملية : 1 نقطة")
      os.remove(req_filename)
      bot.delete_message(m.chat.id, wait.message_id)
    except Exception as e:
      bot.edit_message_text(chat_id=m.chat.id, message_id=wait.message_id, text=f"❌ حدث خطأ: <code>{str(e)[:150]}</code>")
    del user_states[uid]
    return

  if action == "waiting_error_check_file":
    if m.content_type != "document" or not m.document.file_name.endswith(".py"):
      bot.reply_to(m, "❌ يرجى إرسال ملف بايثون بصيغة <code>.py</code> حصراً لفحصه!")
      return

    if not check_and_deduct_point(uid, m.chat.id):
      del user_states[uid]
      return

    wait = bot.reply_to(m, "⏳ <b>جاري فحص كود الملف برمجياً للبحث عن أخطاء...</b>")
    try:
      file_info = bot.get_file(m.document.file_id)
      downloaded = bot.download_file(file_info.file_path)
      try:
        content_str = downloaded.decode("utf-8")
      except:
        content_str = downloaded.decode("latin-1")

      compile(content_str, m.document.file_name, 'exec')

      kb = InlineKeyboardMarkup()
      kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back", style="danger"))
      bot.edit_message_text(
          chat_id=m.chat.id,
          message_id=wait.message_id,
          text=f"✅ <b>الملف سليم تماماً!</b>\n💰 تكلفة العملية : 1 نقطة\n\n📂 الملف: <code>{m.document.file_name}</code>\n💡 <b>لا توجد أي أخطاء برمجية (SyntaxError) أو مشاكل في الأقواس.</b>",
          reply_markup=kb
      )
    except SyntaxError as se:
      error_msg = f"خطأ في السطر {se.lineno}: {se.text}\n{se.msg}"
      kb = InlineKeyboardMarkup()
      kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back", style="danger"))
      bot.edit_message_text(
          chat_id=m.chat.id,
          message_id=wait.message_id,
          text=f"❌ <b>تم اكتشاف خطأ برمجي في الملف!</b>\n💰 تكلفة العملية : 1 نقطة\n\n<code>{error_msg}</code>",
          reply_markup=kb
      )
    except Exception as e:
      kb = InlineKeyboardMarkup()
      kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back", style="danger"))
      bot.edit_message_text(
          chat_id=m.chat.id,
          message_id=wait.message_id,
          text=f"❌ <b>حدث خطأ أثناء تحليل الملف:</b>\n<code>{str(e)[:150]}</code>",
          reply_markup=kb
      )
    del user_states[uid]
    return

  if action != "waiting_file":
    bot.reply_to(m, "❌ يرجى الضغط على زر القسم المطلوب أولاً!")
    return

  if not m.document.file_name.endswith(".py"):
    bot.reply_to(m, "❌ يرجى إرسال ملفات بصيغة بايثون <code>.py</code> فقط!")
    return

  if m.document.file_size > 1024 * 1024:
    bot.reply_to(m, "❌ عذراً، حجم الملف كبير جداً! الحد الأقصى المسموح هو 1MB.")
    return

  # خصم النقطة عند إرسال ملف التلوين وقبوله
  if not check_and_deduct_point(uid, m.chat.id):
    del user_states[uid]
    return

  wait = bot.reply_to(m, "⏳ <b>جاري فحص الملف وتحليل الأزرار... ريثما يتم الانتهاء 🔄</b>")

  try:
    file_info = bot.get_file(m.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    try:
      original = downloaded.decode("utf-8")
    except:
      original = downloaded

    buttons = find_all_buttons(original)
    buttons_count = len(buttons)

    if buttons_count == 0:
      bot.edit_message_text(
          "⚠️ <b>عذراً، لم يتم العثور على أزرار شفافة (InlineKeyboardButton) في داخل هذا الملف!</b>",
          m.chat.id,
          wait.message_id,
      )
      del user_states[uid]
      return

    user_states[uid] = {
        "action": "waiting_color",
        "file_name": m.document.file_name,
        "file_content": downloaded,
        "buttons": buttons,
        "buttons_count": buttons_count,
        "colored_buttons": {},
        "text_modifications": {},
        "current_page": 0,
    }

    kb = get_color_menu(buttons_count)
    buttons_preview = "\n".join([f"• <code>{btn['text'][:30]}</code>" for btn in buttons[:10]])
    if buttons_count > 10:
      buttons_preview += f"\n... و {buttons_count - 10} أزرار أخرى إضافية."

    txt = f"""<blockquote>🎨 <b>تم استخلاص وفحص الملف بنجاح!</b>

💰 تكلفة العملية : 1 نقطة
📂 <b>اسم الملف:</b> <code>{m.document.file_name}</code>
🎯 <b>عدد الأزرار المكتشفة:</b> <b>{buttons_count}</b> زر
📊 <b>نقاطك الحالية:</b> <b>{'لانهائي ♾️' if uid == ADMIN_ID else current_user['points']}</b> نقطة

📋 <b>عينة من أسماء الأزرار المكتشفة:</b>
{buttons_preview}

━━━━━━━━━━━━━━━━━━━━━
🎨 <b>يرجى اختيار طريقة التلوين المطلوبة:</b></blockquote>"""

    send_or_edit_menu(m.chat.id, wait.message_id, txt, kb, is_navigation=True)

  except Exception as e:
    bot.edit_message_text(
        f"❌ حدث خطأ غير متوقع أثناء معالجة الملف:\n<code>{str(e)[:200]}</code>",
        m.chat.id,
        wait.message_id,
    )
    del user_states[uid]

@bot.callback_query_handler(
    func=lambda c: c.data
    in [
        "select_buttons",
        "back_to_color",
        "confirm_custom_color",
        "finish_force_sub",
    ]
    or c.data.startswith(("set_color_", "select_page_"))
)
def color_selection_handler(c):
  global total_colored
  uid = c.from_user.id

  if uid not in user_states:
    bot.answer_callback_query(c.id, "انتهت الجلسة، الرجاء البدء من جديد", True)
    return

  state = user_states[uid]

  if c.data == "finish_force_sub":
    channels = state.get("channels", [])
    if not channels:
      bot.answer_callback_query(c.id, "❌ لم تقم بإرسال أي قناة أو مجموعة حتى الآن!", True)
      return
    
    file_content = state.get("file_content")
    try:
      original = file_content.decode("utf-8")
    except:
      original = file_content

    channels_repr = repr(channels)
    force_sub_snippet = f"""
# ==================== نظام الاشتراك الإجباري ====================
FORCE_CHANNELS = {channels_repr}

def check_sub(bot_inst, user_id):
    for ch in FORCE_CHANNELS:
        try:
            res = bot_inst.get_chat_member(ch, user_id)
            if res.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

@bot.message_handler(commands=['start'])
def force_sub_start_wrapper(message):
    if not check_sub(bot, message.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        for idx, ch in enumerate(FORCE_CHANNELS):
            kb.add(InlineKeyboardButton(f"اشتراك في القناة {{idx+1}}", url=f"https://t.me/{{ch.replace('@','')}}"))
        kb.add(InlineKeyboardButton("✅ اشتركت، تحقق", callback_data="check_force_sub"))
        bot.send_message(message.chat.id, "❌ <b>عذراً، يجب عليك الاشتراك في القنوات أدناه لاستخدام البوت!</b>", reply_markup=kb)
        return
"""
    updated_content = force_sub_snippet + "\n\n" + original
    
    timestamp = int(time.time())
    filename = f"forcesub_{timestamp}_bot.py"
    with open(filename, "wb") as f:
      f.write(updated_content.encode("utf-8"))

    with open(filename, "rb") as f:
      bot.send_document(c.message.chat.id, f, caption="✅ <b>تم إضافة نظام الاشتراك الإجباري إلى ملفك بنجاح تام!</b>")
    os.remove(filename)
    del user_states[uid]
    bot.answer_callback_query(c.id, "تم إرسال الملف المعدل بنجاح!")
    return

  if c.data == "back_to_color":
    state["action"] = "waiting_color"
    user_states[uid] = state
    kb = get_color_menu(state.get("buttons_count", 0))
    txt = (
        "🎨 <b>اختر طريقة التلوين المطلوبة:</b>\n\n📊 إجمالي الأزرار المكتشفة في"
        f" الملف: <b>{state.get('buttons_count', 0)}</b>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if c.data == "select_buttons":
    buttons_list = state.get("buttons", [])
    state["action"] = "selecting_buttons"
    state.setdefault("colored_buttons", {})
    state.setdefault("text_modifications", {})
    state["current_page"] = 0
    user_states[uid] = state

    colored_dict = state.get("colored_buttons", {})
    text_mods = state.get("text_modifications", {})
    index = state.get("current_page", 0)

    kb, total_btns, colored_count, current_idx, total_pages = (
        get_buttons_selection_menu(buttons_list, colored_dict, text_mods, index)
    )
    total_mod = len(set(list(colored_dict.keys()) + list(text_mods.keys())))
    txt = (
        "<blockquote>🎨 <b>اختر اللون المناسب لكل زر يدوياً:</b>\n\n📊 إجمالي الأزرار:"
        f" <b>{total_btns}</b>\n🎨 الأزرار المعدلة:"
        f" <b>{total_mod}</b>\n📍 الزر الحالي:"
        f" <b>{current_idx} من {total_pages}</b></blockquote>"
    )
    send_or_edit_menu(c.message.chat.id, c.message.message_id, txt, kb, is_navigation=True)
    bot.answer_callback_query(c.id)
    return

  if c.data.startswith("set_color_"):
    parts = c.data.split("_")
    btn_index = int(parts[2])
    color_style = parts[3]

    colored_dict = state.get("colored_buttons", {})
    colored_dict[str(btn_index)] = color_style
    state["colored_buttons"] = colored_dict
    user_states[uid] = state

    buttons_list = state.get("buttons", [])
    text_mods = state.get("text_modifications", {})
    index = state.get("current_page", 0)
    kb, total_btns, colored_count, current_idx, total_pages = (
        get_buttons_selection_menu(buttons_list, colored_dict, text_mods, index)
    )
    
    total_mod = len(set(list(colored_dict.keys()) + list(text_mods.keys())))
    txt = (
        "<blockquote>🎨 <b>اختر اللون المناسب لكل زر يدوياً:</b>\n\n📊 إجمالي الأزرار:"
        f" <b>{total_btns}</b>\n🎨 الأزرار المعدلة:"
        f" <b>{total_mod}</b>\n📍 الزر الحالي:"
        f" <b>{current_idx} من {total_pages}</b></blockquote>"
    )

    try:
      bot.edit_message_caption(
          chat_id=c.message.chat.id,
          message_id=c.message.message_id,
          caption=txt,
          reply_markup=kb
      )
    except Exception:
      pass

    color_arabic = (
        "الأحمر 🔴"
        if color_style == "danger"
        else ("الأزرق 🔵" if color_style == "primary" else "الأخضر 🟢")
    )
    bot.answer_callback_query(c.id, f"✅ تم تعيين اللون {color_arabic} للزر")
    return

  if c.data.startswith("select_page_"):
    index = int(c.data.split("_")[-1])
    state["current_page"] = index
    user_states[uid] = state
    buttons_list = state.get("buttons", [])
    colored_dict = state.get("colored_buttons", {})
    text_mods = state.get("text_modifications", {})
    kb, total_btns, colored_count, current_idx, total_pages = (
        get_buttons_selection_menu(buttons_list, colored_dict, text_mods, index)
    )
    
    total_mod = len(set(list(colored_dict.keys()) + list(text_mods.keys())))
    txt = (
        "<blockquote>🎨 <b>اختر اللون المناسب لكل زر يدوياً:</b>\n\n📊 إجمالي الأزرار:"
        f" <b>{total_btns}</b>\n🎨 الأزرار المعدلة:"
        f" <b>{total_mod}</b>\n📍 الزر الحالي:"
        f" <b>{current_idx} من {total_pages}</b></blockquote>"
    )

    try:
      bot.edit_message_caption(
          chat_id=c.message.chat.id,
          message_id=c.message.message_id,
          caption=txt,
          reply_markup=kb
      )
    except Exception:
      pass

    bot.answer_callback_query(c.id)
    return

  if c.data == "confirm_custom_color":
    colored_dict = state.get("colored_buttons", {})
    text_mods = state.get("text_modifications", {})
    if not colored_dict and not text_mods:
      bot.answer_callback_query(c.id, "❌ لم تقم بتعديل أو تلوين أي زر حتى الآن!", True)
      return

    file_content = state["file_content"]
    try:
      original = file_content.decode("utf-8")
    except:
      original = file_content

    colored = process_final_file(original, colored_dict, text_mods)

    if colored:
      users_data[str(uid)]["colored_files"] = (
          users_data[str(uid)].get("colored_files", 0) + 1
      )
      total_colored += 1
      timestamp = int(time.time())
      filename = f"colored_{timestamp}_{state['file_name']}"
      with open(filename, "wb") as f:
        f.write(colored.encode("utf-8"))
      
      total_mod = len(set(list(colored_dict.keys()) + list(text_mods.keys())))
      caption = (
          "✅ <b>تم تعديل وتلوين الأزرار المحددة بنجاح تام!</b>\n\n📂 الملف:"
          f" <code>{state['file_name']}</code>\n🎨 الطريقة: تخصيص وتعديل يدوي"
          f"\n🎯 عدد التعديلات المطبقة:"
          f" <b>{total_mod}</b>\n💰 نقاطي المتبقية:"
          " <b>"
          f"{'لانهائي ♾️' if uid == ADMIN_ID else users_data[str(uid)]['points']}</b>"
      )
      with open(filename, "rb") as f:
        bot.send_document(c.message.chat.id, f, caption=caption)
      os.remove(filename)
      del user_states[uid]
      kb, pts, vip = get_main_keyboard(uid)
      welcome_text = (
          "<blockquote><b>أهلاً بك مجدداً 🎨</b>\n\n"
          "ℹ️ <b>توضيح نظام النقاط:</b>\n"
          "• عند استخدام أي ميزة (إرسال ملف أو فحص توكن) سيتم خصم <b>نقطة واحدة (1)</b> فقط عند إتمام العملية بنجاح.\n"
          "• عند دعوة صديق عبر رابط الدعوة الخاص بك، ستربح <b>نقطة واحدة (1)</b>!\n"
          "• يمكنك أيضاً الحصول على نقاط مجانية يومياً عبر زر <b>الهدية اليومية 🎁</b>.</blockquote>"
      )
      bot.send_photo(
          c.message.chat.id,
          PHOTO_URL,
          caption=welcome_text,
          reply_markup=kb,
      )
    bot.answer_callback_query(c.id)
    return

if __name__ == "__main__":
  print("=" * 50)
  print("🎨 COLOR BUTTONS BOT")
  print("=" * 50)
  print(f"👑 Admin: {ADMIN_ID} (Points: Infinite)")
  print("=" * 50)
  print("✅ البوت يعمل الآن بنجاح...")
  print("=" * 50)

  try:
    bot.delete_webhook()
  except:
    pass

  bot.infinity_polling(timeout=60)
