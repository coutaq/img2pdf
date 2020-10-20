import array
from reportlab.pdfgen.canvas import Canvas
from PIL import Image
from datetime import datetime
from reportlab.lib.pagesizes import A4
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram import File, Bot, InputFile
from collections import deque
from io import BytesIO, BufferedReader, BufferedIOBase, BufferedWriter
import sys
import os
 
botToken = str(sys.argv[1])
updater = Updater(token=botToken, use_context=True)
bot = Bot(token=botToken)
photos = deque()
dispatcher = updater.dispatcher
pdfs = {}

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="A bot for converting images to a pdf file.\nTo start, use the command /upload <Название>.\nMade by Michael Melikov.")

def upload(update, context):
    user = update.message.from_user
    chat = update.effective_chat.id
    if(not context.args):
        context.args = ["{} {}.pdf".format(user.first_name, user.username)]
    filename = context.args[0]
    pdfs[chat] = PDF(chat, user.username, filename)
    context.bot.send_message(chat_id=chat, text="Upload images up to 20mb per image.\nWhen you're done use /create to create the pdf")

def getPhoto(update, context):
    pdf = pdfs[update.effective_chat.id]
    pdf.append(update.message.photo[-1].file_id)


def getFile(update, context):
    photos.append(update.message.document.file_id)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Document succesfully uploaded!")

def create(update, context):
    chat = update.effective_chat.id
    pdf = pdfs[chat]
    pdf.createPFD()
    pdf.uploadPDF()
    pdfs.pop(chat)

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('upload', upload))
dispatcher.add_handler(CommandHandler('create', create))
dispatcher.add_handler(MessageHandler(Filters.photo & (~Filters.command), getPhoto))
dispatcher.add_handler(MessageHandler(Filters.document.category("image") & (~Filters.command), getFile))

updater.start_polling()

class PDF:
    def __init__(self, chat_id, user_id, filename):
        self.chat_id = chat_id
        self.user_id = user_id
        if(not filename.endswith(".pdf")):
            filename+=".pdf"
        self.filename = filename
        self.images = deque()
        print("{}:User @{}(chat_id:{}) created {}.".format(datetime.now(), chat_id, user_id, filename))

    def append(self, image):
        bot.send_message(chat_id=self.chat_id, text="Photo succesfully uploaded!")
        self.images.append(image)

    def createPFD(self):
        print("{}:User @{}(chat_id:{}) uploaded and combined the pictures into {}.".format(datetime.now(), self.chat_id, self.user_id, self.filename))
        canvas = Canvas(filename=self.filename)
        for image in self.images:
            bytes = BytesIO(bot.getFile(image).download_as_bytearray())  
            page = Image.open(bytes).convert("RGBA")
            bytes.close()
            page_width, page_height = page.size
            draw_width, draw_height = page_width, page_height
            if page_width > page_height:
                canvas.setPageSize((draw_width, draw_height))
            else:
                canvas.setPageSize((draw_width, draw_height))
            canvas.drawInlineImage(page, 0, 0, width=draw_width, height=draw_height)
            canvas.showPage()
        canvas.save()

    def uploadPDF(self):
        file = open(self.filename, 'rb')
        print("{}:User @{}(chat_id:{}) got theirs pdf {}.".format(datetime.now(), self.chat_id, self.user_id, self.filename))
        bot.send_message(chat_id=self.chat_id, text="Uploading the pdf!")
        bot.send_document(chat_id=self.chat_id, document=file)
        file.close()
        os.remove(self.filename)