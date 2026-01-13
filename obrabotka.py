"""
Модуль для обработки и подготовки аудиофайлов
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging
from dataclasses import dataclass

import ffmpeg
import librosa
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize

logger = logging.getLogger(__name__)

@dataclass
class AudioInfo:
    """Информация об аудиофайле"""
    source_path: str
    processed_path: str
    duration: float
    sample_rate: int
    channels: int
    format: str
    size_mb: float

class AudioProcessor:
    """Класс для обработки аудиофайлов"""
    
    SUPPORTED_FORMATS = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.mp4', '.avi', '.mkv', '.mov']
    
    def __init__(self, config: Dict):
        self.config = config
        self.temp_dir = tempfile.mkdtemp(prefix="subtitle_audio_")
        logger.info(f"Временная директория для аудио: {self.temp_dir}")
    
    def process(self, input_path: str, output_dir: str = None) -> AudioInfo:
        """
        Основной метод обработки аудиофайла
        
        Args:
            input_path: Путь к входному файлу
            output_dir: Директория для сохранения обработанного файла
            
        Returns:
            AudioInfo с информацией о файле
        """
        logger.info(f"Начало обработки аудио: {input_path}")
        
        # Проверка формата
        if not self.is_supported_format(input_path):
            raise ValueError(f"Неподдерживаемый формат файла: {input_path}")
        
        # Извлечение информации о файле
        audio_info = self.analyze_audio(input_path)
        
        # Обработка в зависимости от типа файла
        if self.is_video_file(input_path):
            processed_path = self.extract_audio_from_video(input_path, output_dir)
        else:
            processed_path = self.prepare_audio_file(input_path, output_dir)
        
        audio_info.processed_path = processed_path
        
        # Дополнительная обработка при необходимости
        if self.config['audio_preprocessing']['normalize']:
            processed_path = self.normalize_audio(processed_path)
            audio_info.processed_path = processed_path
        
        if self.config['audio_preprocessing']['noise_reduction']:
            processed_path = self.reduce_noise(processed_path)
            audio_info.processed_path = processed_path
        
        logger.info(f"Аудио обработано: {processed_path}")
        return audio_info
    
    def is_supported_format(self, filepath: str) -> bool:
        """Проверка поддержки формата файла"""
        ext = Path(filepath).suffix.lower()
        return ext in self.SUPPORTED_FORMATS
    
    def is_video_file(self, filepath: str) -> bool:
        """Определение, является ли файл видео"""
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']
        return Path(filepath).suffix.lower() in video_extensions
    
    def analyze_audio(self, filepath: str) -> AudioInfo:
        """Анализ аудиофайла и извлечение информации"""
        try:
            # Используем librosa для получения информации
            duration = librosa.get_duration(path=filepath)
            
            # Используем soundfile для более точной информации
            with sf.SoundFile(filepath) as f:
                sample_rate = f.samplerate
                channels = f.channels
                frames = f.frames
                format_info = str(f.format)
            
            # Размер файла
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            
            return AudioInfo(
                source_path=filepath,
                processed_path="",
                duration=duration,
                sample_rate=sample_rate,
                channels=channels,
                format=format_info,
                size_mb=size_mb
            )
            
        except Exception as e:
            logger.error(f"Ошибка анализа аудиофайла {filepath}: {e}")
            raise
    
    def extract_audio_from_video(self, video_path: str, output_dir: str = None) -> str:
        """Извлечение аудиодорожки из видео"""
        logger.info(f"Извлечение аудио из видео: {video_path}")
        
        if output_dir is None:
            output_dir = self.temp_dir
        
        output_path = Path(output_dir) / f"{Path(video_path).stem}_audio.wav"
        
        try:
            # Используем ffmpeg для извлечения аудио
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(
                stream,
                str(output_path),
                acodec='pcm_s16le',
                ac=self.config['audio_preprocessing']['channels'],
                ar=self.config['audio_preprocessing']['target_sample_rate']
            )
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            
            logger.info(f"Аудио извлечено: {output_path}")
            return str(output_path)
            
        except ffmpeg.Error as e:
            logger.error(f"Ошибка ffmpeg при извлечении аудио: {e.stderr.decode()}")
            raise
    
    def prepare_audio_file(self, audio_path: str, output_dir: str = None) -> str:
        """Подготовка аудиофайла к обработке"""
        logger.info(f"Подготовка аудиофайла: {audio_path}")
        
        if output_dir is None:
            output_dir = self.temp_dir
        
        output_path = Path(output_dir) / f"{Path(audio_path).stem}_prepared.wav"
        
        try:
            # Загрузка аудио
            audio = AudioSegment.from_file(audio_path)
            
            # Применяем настройки
            target_sample_rate = self.config['audio_preprocessing']['target_sample_rate']
            target_channels = self.config['audio_preprocessing']['channels']
            
            # Конвертация в моно при необходимости
            if target_channels == 1 and audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Ресемплинг при необходимости
            if audio.frame_rate != target_sample_rate:
                audio = audio.set_frame_rate(target_sample_rate)
            
            # Экспорт в WAV
            audio.export(
                str(output_path),
                format="wav",
                parameters=["-acodec", "pcm_s16le"]
            )
            
            logger.info(f"Аудио подготовлено: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Ошибка подготовки аудио: {e}")
            raise
    
    def normalize_audio(self, audio_path: str) -> str:
        """Нормализация громкости аудио"""
        logger.info(f"Нормализация громкости: {audio_path}")
        
        output_path = Path(audio_path).parent / f"{Path(audio_path).stem}_normalized.wav"
        
        try:
            # Загрузка аудио
            audio = AudioSegment.from_file(audio_path)
            
            # Нормализация
            normalized = normalize(audio)
            
            # Экспорт
            normalized.export(
                str(output_path),
                format="wav",
                parameters=["-acodec", "pcm_s16le"]
            )
            
            # Удаляем оригинальный файл, если он временный
            if str(audio_path).startswith(self.temp_dir):
                os.remove(audio_path)
            
            logger.info(f"Аудио нормализовано: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Ошибка нормализации: {e}")
            return audio_path  # Возвращаем оригинальный файл при ошибке
    
    def reduce_noise(self, audio_path: str) -> str:
        """Подавление шума в аудио"""
        logger.info(f"Подавление шума: {audio_path}")
        
        try:
            # Пытаемся использовать noisereduce, если установлен
            import noisereduce as nr
            
            # Загрузка аудио
            audio, sample_rate = librosa.load(audio_path, sr=None)
            
            if len(audio.shape) > 1:
                audio = librosa.to_mono(audio)
            
            # Определение участка шума (первые 0.5 секунды)
            noise_samples = int(0.5 * sample_rate)
            if len(audio) > noise_samples:
                noise_clip = audio[:noise_samples]
            else:
                noise_clip = audio[:len(audio)//10]  # 10% от файла
            
            # Применение шумоподавления
            reduced_noise = nr.reduce_noise(
                y=audio,
                sr=sample_rate,
                y_noise=noise_clip,
                prop_decrease=0.75  # Уменьшение шума на 75%
            )
            
            # Сохранение результата
            output_path = Path(audio_path).parent / f"{Path(audio_path).stem}_denoised.wav"
            sf.write(output_path, reduced_noise, sample_rate)
            
            # Удаляем оригинальный файл, если он временный
            if str(audio_path).startswith(self.temp_dir):
                os.remove(audio_path)
            
            logger.info(f"Шумоподавление завершено: {output_path}")
            return str(output_path)
            
        except ImportError:
            logger.warning("Библиотека noisereduce не установлена. Пропускаем шумоподавление.")
            return audio_path
        except Exception as e:
            logger.error(f"Ошибка шумоподавления: {e}")
            return audio_path
    
    def split_large_file(self, audio_path: str, max_duration: int = 300) -> list:
        """
        Разделение большого аудиофайла на части
        
        Args:
            audio_path: Путь к аудиофайлу
            max_duration: Максимальная длительность части в секундах
            
        Returns:
            Список путей к частям файла
        """
        logger.info(f"Разделение файла на части: {audio_path}")
        
        try:
            audio = AudioSegment.from_file(audio_path)
            duration_ms = len(audio)
            max_duration_ms = max_duration * 1000
            
            parts = []
            
            for i in range(0, duration_ms, max_duration_ms):
                start_ms = i
                end_ms = min(i + max_duration_ms, duration_ms)
                
                part = audio[start_ms:end_ms]
                part_path = Path(audio_path).parent / f"{Path(audio_path).stem}_part{i//max_duration_ms}.wav"
                
                part.export(
                    str(part_path),
                    format="wav",
                    parameters=["-acodec", "pcm_s16le"]
                )
                
                parts.append(str(part_path))
                logger.info(f"Создана часть {len(parts)}: {part_path}")
            
            logger.info(f"Файл разделен на {len(parts)} частей")
            return parts
            
        except Exception as e:
            logger.error(f"Ошибка разделения файла: {e}")
            raise
    
    def cleanup_temp_files(self):
        """Очистка временных файлов"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Временная директория очищена: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Не удалось очистить временные файлы: {e}")
    
    def __del__(self):
        """Деструктор для очистки временных файлов"""
        self.cleanup_temp_files()