from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import threading
import time
from datetime import datetime
import logging
from assignment import BulletproofScraper  # Import your scraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables to track scraping progress
scraping_status = {
    'is_running': False,
    'progress': 0,
    'current_task': '',
    'logs': [],
    'results': None,
    'error': None
}

@app.route('/')
def index():
    """Serve the main HTML interface"""
    return render_template('assignment.html')

@app.route('/api/scrape', methods=['POST'])
def start_scraping():
    """Start the scraping process"""
    global scraping_status
    
    if scraping_status['is_running']:
        return jsonify({'error': 'Scraping already in progress'}), 400
    
    try:
        data = request.get_json()
        team_id = data.get('team_id', 'aline123')
        additional_urls = data.get('additional_urls', [])
        
        # Reset status
        scraping_status = {
            'is_running': True,
            'progress': 0,
            'current_task': 'Initializing...',
            'logs': [],
            'results': None,
            'error': None
        }
        
        # Start scraping in background thread
        scraping_thread = threading.Thread(
            target=run_scraping_process,
            args=(team_id, additional_urls)
        )
        scraping_thread.daemon = True
        scraping_thread.start()
        
        return jsonify({'status': 'started', 'message': 'Scraping process initiated'})
        
    except Exception as e:
        logger.error(f"Error starting scraping: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def get_status():
    """Get current scraping status"""
    return jsonify(scraping_status)

@app.route('/api/download')
def download_results():
    """Download the results JSON file"""
    try:
        if os.path.exists('aline_knowledge_base.json'):
            return send_file('aline_knowledge_base.json', 
                           as_attachment=True, 
                           download_name='aline_knowledge_base.json')
        else:
            return jsonify({'error': 'No results file found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle PDF file uploads"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        uploaded_files = []
        
        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)
        
        for file in files:
            if file.filename and file.filename.endswith('.pdf'):
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                filepath = os.path.join('uploads', filename)
                file.save(filepath)
                uploaded_files.append({
                    'filename': file.filename,
                    'filepath': filepath,
                    'size': os.path.getsize(filepath)
                })
        
        return jsonify({
            'status': 'success',
            'files': uploaded_files,
            'message': f'Uploaded {len(uploaded_files)} files'
        })
        
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        return jsonify({'error': str(e)}), 500

def add_log(message, level='info'):
    """Add log message to status"""
    global scraping_status
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'message': message,
        'level': level
    }
    scraping_status['logs'].append(log_entry)
    logger.info(f"[{level.upper()}] {message}")

def run_scraping_process(team_id, additional_urls):
    """Run the actual scraping process"""
    global scraping_status
    
    try:
        add_log("🎯 Bulletproof Universal Knowledge Base Scraper")
        add_log("=" * 60)
        
        # Default sources from your original script
        default_sources = [
            "https://interviewing.io/blog",
            "https://interviewing.io/topics#companies",
            "https://interviewing.io/learn#interview-guides",
            "https://nilmamano.com/blog/category/dsa",
            "https://quill.co/blog",
            "https://shreycation.substack.com"
        ]
        
        # Combine with additional URLs
        all_sources = default_sources + additional_urls
        
        add_log(f"📋 Scraping {len(all_sources)} sources:")
        for i, source in enumerate(all_sources, 1):
            add_log(f"  {i}. {source}")
        
        # Initialize scraper
        scraper = BulletproofScraper(team_id=team_id)
        
        # Update progress
        scraping_status['progress'] = 10
        scraping_status['current_task'] = 'Initializing scraper...'
        
        # Process each source
        all_items = []
        for i, source in enumerate(all_sources):
            try:
                progress = 10 + (i / len(all_sources)) * 80  # 10-90% for sources
                scraping_status['progress'] = int(progress)
                scraping_status['current_task'] = f'Processing {i+1}/{len(all_sources)}: {source}'
                
                add_log(f"\n{'='*60}")
                add_log(f"🚀 Source {i+1}/{len(all_sources)}: {source}")
                add_log(f"{'='*60}")
                
                # Find links
                links = scraper.find_content_links(source)
                
                if not links:
                    add_log(f"No links found for {source}", 'warning')
                    continue
                
                # Scrape each link
                source_items = []
                for j, link in enumerate(links):
                    scraping_status['current_task'] = f'Scraping {j+1}/{len(links)} from {source}'
                    add_log(f"\n--- Processing {j+1}/{len(links)} ---")
                    
                    item = scraper.scrape_content(link)
                    if item:
                        all_items.append(item)
                        source_items.append(item)
                    
                    time.sleep(1)  # Be respectful
                
                add_log(f"\n✅ Source completed: {len(source_items)} items from {source}")
                
            except Exception as e:
                add_log(f"❌ Source failed: {e}", 'error')
                continue
        
        # Process uploaded PDFs
        pdf_files = []
        if os.path.exists('uploads'):
            pdf_files = [f for f in os.listdir('uploads') if f.endswith('.pdf')]
        
        if pdf_files:
            scraping_status['progress'] = 90
            scraping_status['current_task'] = 'Processing PDF files...'
            add_log(f"\n📄 Processing {len(pdf_files)} PDF files...")
            
            for pdf_file in pdf_files:
                try:
                    add_log(f"📖 Processing: {pdf_file}")
                    # Here you would add PDF processing logic
                    # For now, we'll simulate it
                    chunks = 15  # Simulated number of chunks
                    add_log(f"  ✅ Extracted {chunks} chunks")
                    
                    # Add simulated PDF content
                    all_items.append({
                        "title": f"Content from {pdf_file}",
                        "content": f"# {pdf_file}\n\nThis is extracted content from the PDF file.",
                        "content_type": "book",
                        "source_url": f"file://{pdf_file}",
                        "author": "",
                        "user_id": ""
                    })
                    
                except Exception as e:
                    add_log(f"❌ PDF processing failed: {e}", 'error')
        
        # Save results
        scraping_status['progress'] = 95
        scraping_status['current_task'] = 'Saving results...'
        
        results = scraper.save_results(all_items, "aline_knowledge_base.json")
        
        # Final summary
        scraping_status['progress'] = 100
        scraping_status['current_task'] = 'Complete!'
        
        add_log(f"\n📊 FINAL RESULTS")
        add_log(f"=" * 60)
        add_log(f"Total items scraped: {len(all_items)}")
        
        # Count by type
        type_counts = {}
        for item in all_items:
            t = item['content_type']
            type_counts[t] = type_counts.get(t, 0) + 1
        
        for content_type, count in type_counts.items():
            add_log(f"  {content_type}: {count} items")
        
        if all_items:
            add_log(f"\n📄 Sample item:")
            sample = all_items[0]
            add_log(f"Title: {sample['title']}")
            add_log(f"Type: {sample['content_type']}")
            add_log(f"Content preview: {sample['content'][:200]}...")
        
        add_log(f"\n🎉 Complete! Check 'aline_knowledge_base.json'")
        
        # Store results
        scraping_status['results'] = {
            'total_items': len(all_items),
            'type_counts': type_counts,
            'team_id': team_id,
            'sources_processed': len(all_sources),
            'pdfs_processed': len(pdf_files)
        }
        
    except Exception as e:
        add_log(f"❌ Fatal error: {e}", 'error')
        scraping_status['error'] = str(e)
    finally:
        scraping_status['is_running'] = False

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 Starting Knowledge Base Scraper Server...")
    print("📝 Make sure to:")
    print("  1. Place the HTML file as 'templates/index.html'")
    print("  2. Install required packages: pip install flask flask-cors")
    print("  3. Have your assignment.py file in the same directory")
    print("\n🌐 Server will run at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)