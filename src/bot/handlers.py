#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Handlers Module
معالجات رسائل البوت
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, PhotoSize, Document, Video, Audio, Message
from telegram.ext import ContextTypes
from supabase import Client

from ..core.config import config

logger = logging.getLogger(__name__)


class FileHandler:
    """معالج الملفات"""
    
    def __init__(self, supabase: Client, target_group_id: int):
        self.supabase = supabase
        self.target_group_id = target_group_id
    
    async def handle_file(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """معالج موحد لجميع أنواع الملفات"""
        message = update.message or update.edited_message
        
        if not message or message.chat.id != self.target_group_id:
            return
        
        try:
            file_info = await self._extract_file_info(message, context)
            
            if file_info:
                await self._save_to_database(file_info)
                logger.info(
                    f"✅ تم حفظ الملف: {file_info['file_name']} "
                    f"(النوع: {file_info['file_type']})"
                )
        
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الملف: {e}")
    
    async def _extract_file_info(
        self,
        message: Message,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[Dict[str, Any]]:
        """استخراج معلومات الملف من الرسالة"""
        file_id = None
        file_name = "Unnamed"
        file_type = "unknown"
        file_size = 0
        mime_type = None
        
        # استخراج معلومات حسب نوع الملف
        if message.document:
            doc = message.document
            file_id = doc.file_id
            file_name = doc.file_name or "document"
            file_type = "document"
            file_size = doc.file_size or 0
            mime_type = doc.mime_type
        
        elif message.photo:
            photo = message.photo[-1]  # أكبر حجم
            file_id = photo.file_id
            file_name = f"photo_{message.message_id}.jpg"
            file_type = "photo"
            file_size = photo.file_size or 0
            mime_type = "image/jpeg"
        
        elif message.video:
            video = message.video
            file_id = video.file_id
            file_name = video.file_name or f"video_{message.message_id}.mp4"
            file_type = "video"
            file_size = video.file_size or 0
            mime_type = video.mime_type
        
        elif message.audio:
            audio = message.audio
            file_id = audio.file_id
            file_name = audio.file_name or f"audio_{message.message_id}.mp3"
            file_type = "audio"
            file_size = audio.file_size or 0
            mime_type = audio.mime_type
        
        elif message.voice:
            voice = message.voice
            file_id = voice.file_id
            file_name = f"voice_{message.message_id}.ogg"
            file_type = "voice"
            file_size = voice.file_size or 0
            mime_type = voice.mime_type
        
        if not file_id:
            return None
        
        # الحصول على معلومات الملف من تليجرام
        try:
            file = await context.bot.get_file(file_id)
            file_path = file.file_path
            file_url = config.get_telegram_file_url(file_path.split('/')[-1])
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على معلومات الملف: {e}")
            return None
        
        # استخراج الوصف (Caption)
        caption = message.caption or ""
        
        # استخراج اسم الرافع (إذا كان من الموقع)
        uploaded_by = None
        if caption and "📤 رفع بواسطة:" in caption:
            try:
                uploaded_by = caption.split("📤 رفع بواسطة:")[1].strip()
            except:
                pass
        
        return {
            "file_id": file_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": file_size,
            "file_url": file_url,
            "mime_type": mime_type,
            "message_id": message.message_id,
            "caption": caption,
            "uploaded_by": uploaded_by,
            "uploaded_at": datetime.utcnow().isoformat()
        }
    
    async def _save_to_database(self, file_info: Dict[str, Any]) -> None:
        """حفظ معلومات الملف في قاعدة البيانات"""
        try:
            self.supabase.table('files').insert({
                "telegram_file_id": file_info["file_id"],
                "file_name": file_info["file_name"],
                "file_type": file_info["file_type"],
                "file_size": file_info["file_size"],
                "file_url": file_info["file_url"],
                "mime_type": file_info["mime_type"],
                "message_id": file_info["message_id"],
                "caption": file_info["caption"],
                "uploaded_by": file_info["uploaded_by"],
                "created_at": file_info["uploaded_at"]
            }).execute()
        
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الملف في قاعدة البيانات: {e}")
            raise


class DeletionHandler:
    """معالج حذف الرسائل"""
    
    def __init__(self, supabase: Client, target_group_id: int):
        self.supabase = supabase
        self.target_group_id = target_group_id
    
    async def handle_deletion(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """معالج حذف الرسائل من المجموعة"""
        if not update.message or update.message.chat.id != self.target_group_id:
            return
        
        try:
            # الحصول على معرف الرسالة المحذوفة
            deleted_message_id = update.message.message_id
            
            # حذف السجل من قاعدة البيانات
            result = self.supabase.table('files').delete().eq(
                'message_id', deleted_message_id
            ).execute()
            
            if result.data:
                logger.info(
                    f"✅ تم حذف الملف من قاعدة البيانات "
                    f"(message_id: {deleted_message_id})"
                )
        
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الملف من قاعدة البيانات: {e}")
