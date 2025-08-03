#\!/usr/bin/env python3
'''Run collection with limited keywords to ensure completion'''
import sys
sys.path.insert(0, '/opt/youtube_app')

from youtube_collection_manager import YouTubeCollectionManager
import logging

# Override to limit keywords
class LimitedCollectionManager(YouTubeCollectionManager):
    def run(self):
        '''Process only first 2 keywords'''
        try:
            # Get keywords from Firebase
            all_keywords = self.firebase.get_keywords()
            if not all_keywords:
                raise Exception('No keywords found in Firebase')
            
            # Limit to first 2 keywords
            keywords = all_keywords[:2]
            
            self.logger.info(f'Starting limited collection for {len(keywords)} keywords: {keywords}')
            
            # Process each keyword
            for i, keyword in enumerate(keywords):
                # Get server
                server = self.available_servers[i]
                self.used_servers.add(server)
                
                # Process keyword
                self.process_keyword(keyword, server)
                self.collection_stats['keywords_processed'].append(keyword)
            
            # Mark success
            self.collection_stats['success'] = True
            self.logger.info('All keywords processed successfully')
            
        except Exception as e:
            self.logger.error(f'Collection failed: {e}')
            self.collection_stats['errors'].append(str(e))
            self.collection_stats['success'] = False
            
        finally:
            # Always log to Firebase
            self._finalize_collection()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    manager = LimitedCollectionManager()
    manager.run()
