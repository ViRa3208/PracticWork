#!/usr/bin/env python3
"""
Auto Subtitle Generator v2.0
Полностью автоматическая система генерации субтитров
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('subtitle_generator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AutoSubtitleGenerator:
    """Основной класс для автоматической генерации субтитров"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.load_config(config_path)
        self.setup_components()
        
    def load_config(self, config_path: str):
        """Загрузка конфигурации из YAML файла"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Конфигурация загружена из {config_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            self.config = self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Резервная конфигурация по умолчанию"""
        return {
            'subtitle_settings': {
                'max_chars_per_line': 42,
                'max_lines': 2,
                'min_duration': 1.0,
                'max_duration': 4.0
            }
        }
    
    def setup_components(self):
        """Инициализация всех компонентов системы"""
        from audio_processor import AudioProcessor
        from transcription_manager import TranscriptionManager
        from post_processor import PostProcessor
        from formatter_manager import FormatterManager
        from quality_checker import QualityChecker
        
        self.audio_processor = AudioProcessor(self.config)
        self.transcription_manager = TranscriptionManager(self.config)
        self.post_processor = PostProcessor(self.config)
        self.formatter_manager = FormatterManager(self.config)
        self.quality_checker = QualityChecker(self.config)
        
        logger.info("Все компоненты системы инициализированы")
    
    def process_file(self, input_path: str, output_dir: str = "output",
                    language: str = None, provider: str = "auto") -> Dict:
        """
        Основной метод обработки файла
        
        Args:
            input_path: Путь к входному файлу (аудио/видео)
            output_dir: Директория для выходных файлов
            language: Язык распознавания (None для автоопределения)
            provider: Провайдер ASR ('auto', 'nexara', 'openai', 'fireworks')
        
        Returns:
            Словарь с результатами обработки
        """
        try:
            logger.info(f"Начало обработки: {input_path}")
            
            # 1. Создание выходной директории
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 2. Подготовка аудио
            logger.info("Этап 1: Подготовка аудио...")
            audio_info = self.audio_processor.process(input_path, output_dir)
            
            # 3. Выбор лучшего провайдера
            if provider == "auto":
                provider = self.transcription_manager.select_best_provider(
                    audio_info['duration'],
                    audio_info['size_mb']
                )
            logger.info(f"Выбран провайдер: {provider}")
            
            # 4. Транскрибация
            logger.info("Этап 2: Распознавание речи...")
            transcription = self.transcription_manager.transcribe(
                audio_info['processed_path'],
                provider=provider,
                language=language
            )
            
            # 5. Пост-обработка
            logger.info("Этап 3: Пост-обработка текста...")
            processed_data = self.post_processor.process(transcription)
            
            # 6. Контроль качества
            logger.info("Этап 4: Проверка качества...")
            quality_report = self.quality_checker.check(processed_data['segments'])
            
            # Автоматическая коррекция при необходимости
            if quality_report['total_issues'] > 0:
                logger.warning(f"Обнаружено проблем: {quality_report['total_issues']}")
                if quality_report['errors']:
                    processed_data['segments'] = self.quality_checker.auto_correct(
                        processed_data['segments']
                    )
            
            # 7. Генерация файлов
            logger.info("Этап 5: Создание файлов субтитров...")
            output_files = {}
            
            for format_name in self.config['output_formats']['enabled']:
                output_path = Path(output_dir) / f"{Path(input_path).stem}.{format_name}"
                content = self.formatter_manager.format(
                    processed_data['segments'],
                    format_name
                )
                
                output_path.write_text(content, encoding='utf-8-sig')
                output_files[format_name] = str(output_path)
                logger.info(f"Создан файл: {output_path}")
            
            # 8. Генерация отчета
            report_path = Path(output_dir) / f"{Path(input_path).stem}_report.txt"
            self.generate_report(
                report_path,
                audio_info,
                transcription,
                processed_data,
                quality_report,
                output_files
            )
            
            logger.info(f"Обработка завершена успешно!")
            
            return {
                'success': True,
                'input_file': input_path,
                'output_files': output_files,
                'report': str(report_path),
                'audio_info': audio_info,
                'transcription_stats': {
                    'words': len(processed_data.get('words', [])),
                    'segments': len(processed_data['segments']),
                    'provider': provider,
                    'language': transcription.get('language', 'unknown')
                },
                'quality_report': quality_report
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке файла: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'input_file': input_path
            }
    
    def generate_report(self, report_path: Path, audio_info: Dict, 
                       transcription: Dict, processed_data: Dict,
                       quality_report: Dict, output_files: Dict):
        """Генерация подробного отчета о процессе"""
        report_content = [
            "=" * 60,
            "ОТЧЕТ О ГЕНЕРАЦИИ СУБТИТРОВ",
            "=" * 60,
            f"\nИсходный файл: {audio_info['source_path']}",
            f"Длительность: {audio_info['duration']:.2f} сек",
            f"Размер: {audio_info['size_mb']:.2f} МБ",
            f"Формат: {audio_info['format']}",
            f"\n--- РАСПОЗНАВАНИЕ РЕЧИ ---",
            f"Провайдер: {transcription.get('provider', 'unknown')}",
            f"Язык: {transcription.get('language', 'auto')}",
            f"Распознано слов: {len(processed_data.get('words', []))}",
            f"Сегментов: {len(processed_data['segments'])}",
            f"\n--- КАЧЕСТВО ---",
            f"Всего проблем: {quality_report['total_issues']}",
            f"Ошибки: {len(quality_report['errors'])}",
            f"Предупреждения: {len(quality_report['warnings'])}",
        ]
        
        if quality_report['warnings']:
            report_content.append("\nПредупреждения:")
            for warning in quality_report['warnings'][:5]:  # Первые 5
                report_content.append(f"  • {warning}")
        
        if quality_report['errors']:
            report_content.append("\nКритические ошибки:")
            for error in quality_report['errors'][:5]:
                report_content.append(f"  • {error}")
        
        report_content.append(f"\n--- ВЫХОДНЫЕ ФАЙЛЫ ---")
        for format_name, filepath in output_files.items():
            report_content.append(f"{format_name.upper()}: {filepath}")
        
        report_content.append(f"\n--- СТАТИСТИКА ---")
        total_chars = sum(len(s['text']) for s in processed_data['segments'])
        report_content.append(f"Всего символов: {total_chars}")
        report_content.append(f"Символов/сек: {total_chars/audio_info['duration']:.1f}")
        
        if processed_data.get('words'):
            words_per_min = len(processed_data['words']) / (audio_info['duration'] / 60)
            report_content.append(f"Слов/минуту: {words_per_min:.1f}")
        
        report_content.append(f"\n{'='*60}")
        report_content.append(f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        report_path.write_text('\n'.join(report_content), encoding='utf-8')
    
    def batch_process(self, input_dir: str, output_dir: str = "output_batch",
                     file_patterns: List[str] = None) -> List[Dict]:
        """Пакетная обработка нескольких файлов"""
        if file_patterns is None:
            file_patterns = ['*.mp3', '*.wav', '*.mp4', '*.m4a']
        
        results = []
        input_path = Path(input_dir)
        
        for pattern in file_patterns:
            for file_path in input_path.glob(pattern):
                if file_path.is_file():
                    logger.info(f"Обработка файла: {file_path}")
                    
                    result = self.process_file(
                        str(file_path),
                        output_dir=Path(output_dir) / file_path.stem
                    )
                    results.append(result)
        
        # Генерация сводного отчета
        self.generate_batch_report(results, output_dir)
        
        return results
    
    def generate_batch_report(self, results: List[Dict], output_dir: str):
        """Генерация отчета по пакетной обработке"""
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        report_content = [
            "=" * 60,
            "СВОДНЫЙ ОТЧЕТ ПАКЕТНОЙ ОБРАБОТКИ",
            "=" * 60,
            f"\nВсего файлов: {len(results)}",
            f"Успешно: {len(successful)}",
            f"С ошибками: {len(failed)}",
            f"\n--- СТАТИСТИКА ---"
        ]
        
        if successful:
            total_duration = sum(r['audio_info']['duration'] for r in successful)
            total_words = sum(r['transcription_stats']['words'] for r in successful)
            
            report_content.extend([
                f"Общая длительность: {total_duration/60:.1f} мин",
                f"Всего слов: {total_words}",
                f"Слов в минуту: {total_words/(total_duration/60):.1f}"
            ])
        
        if failed:
            report_content.append("\n--- ФАЙЛЫ С ОШИБКАМИ ---")
            for fail in failed:
                report_content.append(f"  • {fail['input_file']}: {fail['error']}")
        
        report_path = Path(output_dir) / "batch_report.txt"
        report_path.write_text('\n'.join(report_content), encoding='utf-8')
        
        logger.info(f"Сводный отчет сохранен: {report_path}")

def main():
    """Основная функция для запуска из командной строки"""
    parser = argparse.ArgumentParser(
        description='Автоматическая генерация субтитров для аудио/видео файлов'
    )
    parser.add_argument('input', help='Путь к файлу или директории')
    parser.add_argument('-o', '--output', default='output', 
                       help='Выходная директория')
    parser.add_argument('-l', '--language', default=None,
                       help='Язык распознавания (ru, en, etc)')
    parser.add_argument('-p', '--provider', default='auto',
                       choices=['auto', 'nexara', 'openai', 'fireworks'],
                       help='Провайдер ASR')
    parser.add_argument('-b', '--batch', action='store_true',
                       help='Пакетная обработка директории')
    parser.add_argument('--config', default='config.yaml',
                       help='Путь к файлу конфигурации')
    
    args = parser.parse_args()
    
    # Проверка существования входного файла/директории
    if not os.path.exists(args.input):
        logger.error(f"Файл или директория не существует: {args.input}")
        sys.exit(1)
    
    # Инициализация генератора
    try:
        generator = AutoSubtitleGenerator(args.config)
    except Exception as e:
        logger.error(f"Ошибка инициализации: {e}")
        sys.exit(1)
    
    # Обработка
    if args.batch and os.path.isdir(args.input):
        logger.info(f"Пакетная обработка директории: {args.input}")
        results = generator.batch_process(args.input, args.output)
        
        successful = len([r for r in results if r['success']])
        logger.info(f"Обработка завершена. Успешно: {successful}/{len(results)}")
    else:
        logger.info(f"Обработка файла: {args.input}")
        result = generator.process_file(
            args.input,
            args.output,
            args.language,
            args.provider
        )
        
        if result['success']:
            logger.info(f"Файлы сохранены в: {args.output}")
            for format_name, filepath in result['output_files'].items():
                logger.info(f"  {format_name.upper()}: {filepath}")
        else:
            logger.error(f"Ошибка: {result['error']}")
            sys.exit(1)

if __name__ == "__main__":
    from datetime import datetime
    
    # Проверка наличия необходимых модулей
    try:
        import yaml
        import pydub
    except ImportError as e:
        print(f"Ошибка: Не установлены необходимые библиотеки: {e}")
        print("Установите их: pip install -r requirements.txt")
        sys.exit(1)
    
    main()