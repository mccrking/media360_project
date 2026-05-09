"""
Data Quality Validation Module
Ensures data integrity across all layers
"""

import logging
import sqlalchemy as sa
from datetime import datetime

logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg2://news:news@postgres:5432/news_dw"
ENGINE = sa.create_engine(DB_URL)

class DataQualityCheck:
    """Validates data quality dimensions: Completeness, Consistency, Validity."""
    
    def __init__(self):
        self.report = {
            'timestamp': datetime.utcnow().isoformat(),
            'checks': [],
            'status': 'PASS'
        }
    
    def check_completeness(self):
        """Check for NULL values and missing data."""
        logger.info("Checking Completeness...")
        
        with ENGINE.connect() as conn:
            checks = [
                ('articles_detail.title_null', "SELECT COUNT(*) FROM articles_detail WHERE title IS NULL OR title = ''"),
                ('articles_detail.author_null', "SELECT COUNT(*) FROM articles_detail WHERE author = 'Unknown'"),
                ('articles_detail.content_null', "SELECT COUNT(*) FROM articles_detail WHERE content IS NULL OR content = ''"),
            ]
            
            for check_name, query in checks:
                count = conn.execute(sa.text(query)).scalar()
                status = 'PASS' if count == 0 else 'WARN'
                self.report['checks'].append({
                    'name': check_name,
                    'status': status,
                    'value': count
                })
                logger.info(f"  {check_name}: {count} issues")
    
    def check_consistency(self):
        """Check for data consistency across tables."""
        logger.info("Checking Consistency...")
        
        with ENGINE.connect() as conn:
            # Foreign key relationships
            orphaned = conn.execute(
                sa.text("""
                SELECT COUNT(*) FROM quarantine_audit qa
                WHERE NOT EXISTS (
                    SELECT 1 FROM articles_detail ad WHERE ad.article_id = qa.article_id
                )
                """)
            ).scalar()
            
            status = 'PASS' if orphaned == 0 else 'FAIL'
            self.report['checks'].append({
                'name': 'orphaned_audit_records',
                'status': status,
                'value': orphaned
            })
            
            if status == 'FAIL':
                self.report['status'] = 'FAIL'
            
            logger.info(f"  orphaned_audit_records: {orphaned} issues")
    
    def check_validity(self):
        """Check for invalid data values."""
        logger.info("Checking Validity...")
        
        with ENGINE.connect() as conn:
            checks = [
                ('invalid_dates', "SELECT COUNT(*) FROM articles_detail WHERE published_at > NOW()"),
                ('negative_lengths', "SELECT COUNT(*) FROM articles_silver WHERE content_length < 0"),
                ('invalid_scores', "SELECT COUNT(*) FROM articles_silver WHERE data_quality_score > 1 OR data_quality_score < 0"),
            ]
            
            for check_name, query in checks:
                try:
                    count = conn.execute(sa.text(query)).scalar()
                    status = 'PASS' if count == 0 else 'WARN'
                    self.report['checks'].append({
                        'name': check_name,
                        'status': status,
                        'value': count
                    })
                    logger.info(f"  {check_name}: {count} issues")
                except Exception as e:
                    logger.warning(f"  {check_name}: Table might not exist yet")
    
    def generate_report(self):
        """Generate final quality report."""
        passed = sum(1 for c in self.report['checks'] if c['status'] == 'PASS')
        total = len(self.report['checks'])
        
        self.report['summary'] = {
            'total_checks': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': (passed / total * 100) if total > 0 else 0
        }
        
        logger.info(f"Quality Report: {passed}/{total} checks passed ({self.report['summary']['pass_rate']:.1f}%)")
        return self.report


def run_quality_checks():
    """Execute all quality checks."""
    checker = DataQualityCheck()
    checker.check_completeness()
    checker.check_consistency()
    checker.check_validity()
    return checker.generate_report()
