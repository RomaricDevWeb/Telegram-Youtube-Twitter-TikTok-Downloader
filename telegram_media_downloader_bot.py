import os
import subprocess
import yt_dlp
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.error import TelegramError

# API Token for the bot (obtenu via @BotFather)
API_TOKEN = '7824028526:AAHGTpnJrtBWHv3Tz_Iub2XG7oCjPJiUHVU'

# Chemin temporaire pour les téléchargements (attention à bien échapper la barre oblique finale)
TEMP_DOWNLOAD_FOLDER = r'C:\Users\\'

# Limite de taille pour Telegram (50 MB)
TELEGRAM_MAX_SIZE_MB = 50

# Gestion de la progression du téléchargement en temps réel
async def download_progress(d, message):
    if d['status'] == 'downloading':
        percentage = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
        # Mise à jour du message toutes les 10%
        if int(percentage) % 10 == 0:
            await message.edit_text(f"🔄 Progression du téléchargement : {percentage:.2f}%")
    elif d['status'] == 'finished':
        await message.edit_text("✅ Téléchargement terminé, traitement du fichier...")

# Téléchargement de vidéos ou audios (YouTube, Twitter/X, TikTok)
async def download_video(url, destination_folder, message, format="video"):
    try:
        if format == "audio":
            format_type = 'bestaudio/best'
            ext = 'mp3'
        else:
            format_type = 'best'
            ext = 'mp4'

        options = {
            'outtmpl': f'{destination_folder}/%(id)s.%(ext)s',
            'format': format_type,
            'restrictfilenames': True,
            'progress_hooks': [lambda d: asyncio.create_task(download_progress(d, message))],
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"Erreur pendant le téléchargement : {e}")
        return False

# Réduction de la qualité avec ffmpeg en cas de dépassement de la taille limite
def reduce_quality_ffmpeg(video_path, output_path, target_size_mb=50):
    try:
        command = [
            'ffmpeg', '-i', video_path,
            '-b:v', '500k',
            '-vf', 'scale=iw/2:ih/2',
            '-c:a', 'aac',
            '-b:a', '128k',
            output_path
        ]
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la réduction avec ffmpeg : {e}")
        return False

# Handler pour le bouton inline d'aide
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    help_message = (
        "💡 **Aide sur la commande /download** 💡\n\n"
        "Utilisation : `/download <url> [audio]`\n"
        "Exemples :\n"
        "  • `/download https://youtu.be/dQw4w9WgXcQ`\n"
        "  • `/download https://youtu.be/dQw4w9WgXcQ audio`\n\n"
        "Cette commande permet de télécharger une vidéo ou un audio depuis :\n"
        "  • YouTube\n"
        "  • Twitter/X\n"
        "  • TikTok\n\n"
        "Si le fichier téléchargé dépasse 50 MB, le bot réduit automatiquement "
        "la qualité pour respecter la limite imposée par Telegram."
    )
    await query.edit_message_text(help_message, parse_mode="Markdown")

# Handler de la commande /start avec un message d'accueil futuriste détaillé
async def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("💾 Télécharger", callback_data='download_help')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    futuristic_message = (
        "╔════════════════════════════════════════════════════════╗\n"
        "║             🤖 BIENVENUE DANS LE FUTUR 🤖              ║\n"
        "║                                                        ║\n"
        "║  Je suis votre Bot Téléchargeur Hyper-Tech, capable de   ║\n"
        "║  récupérer des vidéos et audios depuis :               ║\n"
        "║    • YouTube                                           ║\n"
        "║    • Twitter/X                                         ║\n"
        "║    • TikTok                                            ║\n"
        "║                                                        ║\n"
        "║  Commande principale :                                 ║\n"
        "║    /download <url> [audio]                             ║\n"
        "║                                                        ║\n"
        "║  Exemple :                                             ║\n"
        "║    /download https://youtu.be/dQw4w9WgXcQ audio        ║\n"
        "║                                                        ║\n"
        "║  Si le fichier téléchargé dépasse 50 MB, le bot ajuste   ║\n"
        "║  automatiquement la qualité pour respecter la limite.  ║\n"
        "║                                                        ║\n"
        "║         🚀 Embarquez vers un monde digital avancé !    ║\n"
        "╚════════════════════════════════════════════════════════╝\n"
        "\n"
        "Appuyez sur le bouton ci-dessous pour obtenir plus d'informations."
    )
    await update.message.reply_text(futuristic_message, reply_markup=reply_markup)

# Handler de la commande /download
async def download(update: Update, context: CallbackContext):
    try:
        message_text = update.message.text
        if any(domain in message_text for domain in ["https://www.youtube.com/", "https://youtu.be/", "https://twitter.com/", "https://x.com/", "https://www.tiktok.com/"]):
            params = message_text.split(" ")
            url = params[1]
            format = "video" if len(params) < 3 or params[2].lower() != "audio" else "audio"
            destination_folder = TEMP_DOWNLOAD_FOLDER

            message = await update.message.reply_text(f"🛠️ Démarrage du téléchargement {format} pour : {url}")

            success_download = await download_video(url, destination_folder, message, format)

            if not success_download:
                await message.edit_text("❌ Erreur lors du téléchargement. Veuillez réessayer plus tard.")
                return

            video_filename = max([os.path.join(destination_folder, f) for f in os.listdir(destination_folder)], key=os.path.getctime)
            file_size_mb = os.path.getsize(video_filename) / (1024 * 1024)
            if file_size_mb > TELEGRAM_MAX_SIZE_MB:
                await message.edit_text(f"⚠️ Fichier trop volumineux ({file_size_mb:.2f} MB).\nRéduction de la qualité en cours...")

                output_filename = os.path.join(destination_folder, 'compressed_' + os.path.basename(video_filename))
                success_reduce = reduce_quality_ffmpeg(video_filename, output_filename, TELEGRAM_MAX_SIZE_MB)

                if not success_reduce:
                    await message.edit_text("❌ Erreur lors de la réduction de la qualité. Veuillez réessayer plus tard.")
                    return

                video_filename = output_filename

            await message.edit_text(f"📤 Envoi du {format}...")
            try:
                await update.message.reply_video(video=open(video_filename, 'rb'))
            except TelegramError as e:
                await message.edit_text(f"❌ Erreur lors de l'envoi du fichier : {e}")
                print(f"Erreur lors de l'envoi du fichier : {e}")
            finally:
                if os.path.exists(video_filename):
                    os.remove(video_filename)
        else:
            await update.message.reply_text("Veuillez fournir une URL valide provenant de YouTube, Twitter/X ou TikTok.")
    except Exception as e:
        await update.message.reply_text("Une erreur inattendue est survenue. Veuillez réessayer plus tard.")
        print(f"Erreur dans la fonction download : {e}")

# Fonction principale pour lancer le bot
def main():
    application = ApplicationBuilder().token(API_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('download', download))
    application.add_handler(CallbackQueryHandler(button_handler, pattern='download_help'))
    application.run_polling()

if __name__ == "__main__":
    main()
        
