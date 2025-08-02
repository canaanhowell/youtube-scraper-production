#\!/usr/bin/env python3
'''Test collection with single keyword to demonstrate complete flow'''
import sys
sys.path.insert(0, '/opt/youtube_scraper')

from youtube_collection_manager import YouTubeCollectionManager
import logging

# Override to test with just one keyword
class TestCollectionManager(YouTubeCollectionManager):
    def run(self):
        '''Test with just midjourney keyword'''
        try:
            # Manually set just one keyword
            keywords = ['midjourney']
            
            self.logger.info(f'Starting test collection for {len(keywords)} keyword')
            
            # Process the keyword
            server = self.available_servers[0]  # Use first available server
            self.used_servers.add(server)
            
            self.process_keyword(keywords[0], server)
            self.collection_stats['keywords_processed'].append(keywords[0])
            
            # Mark success
            self.collection_stats['success'] = True
            self.logger.info('Test keyword processed successfully')
            
        except Exception as e:
            self.logger.error(f'Collection failed: {e}')
            self.collection_stats['errors'].append(str(e))
            self.collection_stats['success'] = False
            
        finally:
            # Always log to Firebase
            self._finalize_collection()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    manager = TestCollectionManager()
    manager.run()
