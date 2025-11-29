#!/usr/bin/env python3
"""
Repository Cache Module

Provides caching functionality for repository data, analysis results,
and outdated package checks to improve performance and reduce API calls.

Cache expiry time is configurable via CACHE_EXPIRY_HOURS environment variable.
"""

import os
import json
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()


class RepositoryCache:
    """
    Manages caching of repository data with TTL-based expiration.

    Caches:
    - Repository clones (on disk)
    - Dependency analysis results
    - Outdated package information
    """

    def __init__(self, cache_dir: Optional[str] = None, expiry_hours: Optional[int] = None):
        """
        Initialize repository cache.

        Args:
            cache_dir: Directory to store cache (default: .cache/repos)
            expiry_hours: Cache expiry in hours (default: from env or 24 hours)
        """
        # Cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / '.cache' / 'ai-dependency-updater'

        # Cache expiry time from environment variable or default
        if expiry_hours is not None:
            self.expiry_hours = expiry_hours
        else:
            self.expiry_hours = int(os.getenv('CACHE_EXPIRY_HOURS', '24'))

        # Create cache directories
        self.repos_dir = self.cache_dir / 'repos'
        self.metadata_dir = self.cache_dir / 'metadata'

        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _get_repo_cache_key(self, repo_url: str) -> str:
        """
        Generate a cache key from repository URL.

        Args:
            repo_url: Repository URL or owner/repo format

        Returns:
            Sanitized cache key
        """
        # Extract owner/repo from URL
        if '/' in repo_url:
            if 'github.com' in repo_url:
                # https://github.com/owner/repo -> owner_repo
                parts = repo_url.rstrip('/').split('/')
                cache_key = f"{parts[-2]}_{parts[-1]}"
            else:
                # owner/repo -> owner_repo
                cache_key = repo_url.replace('/', '_')
        else:
            cache_key = repo_url

        # Remove .git suffix if present
        cache_key = cache_key.replace('.git', '')

        return cache_key

    def _get_metadata_path(self, cache_key: str) -> Path:
        """Get path to metadata file for a cache key."""
        return self.metadata_dir / f"{cache_key}.json"

    def _get_repo_path(self, cache_key: str) -> Path:
        """Get path to cached repository."""
        return self.repos_dir / cache_key

    def _is_cache_valid(self, metadata_path: Path) -> bool:
        """
        Check if cache is still valid based on TTL.

        Args:
            metadata_path: Path to metadata file

        Returns:
            True if cache is valid, False if expired
        """
        if not metadata_path.exists():
            return False

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            cached_time = datetime.fromisoformat(metadata.get('cached_at'))
            expiry_time = cached_time + timedelta(hours=self.expiry_hours)

            return datetime.now() < expiry_time

        except (json.JSONDecodeError, ValueError, KeyError):
            return False

    def get_cached_repository(self, repo_url: str) -> Optional[str]:
        """
        Get cached repository path if valid.

        Args:
            repo_url: Repository URL

        Returns:
            Path to cached repository or None if not cached/expired
        """
        cache_key = self._get_repo_cache_key(repo_url)
        metadata_path = self._get_metadata_path(cache_key)
        repo_path = self._get_repo_path(cache_key)

        if self._is_cache_valid(metadata_path) and repo_path.exists():
            return str(repo_path)

        return None

    def cache_repository(self, repo_url: str, repo_path: str) -> None:
        """
        Cache a repository clone.

        Args:
            repo_url: Repository URL
            repo_path: Path to cloned repository
        """
        cache_key = self._get_repo_cache_key(repo_url)
        cached_repo_path = self._get_repo_path(cache_key)
        metadata_path = self._get_metadata_path(cache_key)

        # Copy repository to cache
        if cached_repo_path.exists():
            shutil.rmtree(cached_repo_path)

        shutil.copytree(repo_path, cached_repo_path, symlinks=True)

        # Save metadata
        metadata = {
            'repo_url': repo_url,
            'cached_at': datetime.now().isoformat(),
            'expiry_hours': self.expiry_hours
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def get_cached_analysis(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis results.

        Args:
            repo_url: Repository URL

        Returns:
            Cached analysis data or None
        """
        cache_key = self._get_repo_cache_key(repo_url)
        metadata_path = self._get_metadata_path(cache_key)

        if not self._is_cache_valid(metadata_path):
            return None

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            return metadata.get('analysis')

        except (json.JSONDecodeError, KeyError):
            return None

    def cache_analysis(self, repo_url: str, analysis_data: Dict[str, Any]) -> None:
        """
        Cache analysis results.

        Args:
            repo_url: Repository URL
            analysis_data: Analysis results to cache
        """
        cache_key = self._get_repo_cache_key(repo_url)
        metadata_path = self._get_metadata_path(cache_key)

        # Load or create metadata
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                'repo_url': repo_url,
                'cached_at': datetime.now().isoformat(),
                'expiry_hours': self.expiry_hours
            }

        # Add analysis data
        metadata['analysis'] = analysis_data
        metadata['analysis_cached_at'] = datetime.now().isoformat()

        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def get_cached_outdated(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached outdated packages information.

        Args:
            repo_url: Repository URL

        Returns:
            Cached outdated packages data or None
        """
        cache_key = self._get_repo_cache_key(repo_url)
        metadata_path = self._get_metadata_path(cache_key)

        if not self._is_cache_valid(metadata_path):
            return None

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            return metadata.get('outdated_packages')

        except (json.JSONDecodeError, KeyError):
            return None

    def cache_outdated(self, repo_url: str, outdated_data: Dict[str, Any]) -> None:
        """
        Cache outdated packages information.

        Args:
            repo_url: Repository URL
            outdated_data: Outdated packages data to cache
        """
        cache_key = self._get_repo_cache_key(repo_url)
        metadata_path = self._get_metadata_path(cache_key)

        # Load or create metadata
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                'repo_url': repo_url,
                'cached_at': datetime.now().isoformat(),
                'expiry_hours': self.expiry_hours
            }

        # Add outdated packages data
        metadata['outdated_packages'] = outdated_data
        metadata['outdated_cached_at'] = datetime.now().isoformat()

        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def invalidate_cache(self, repo_url: str) -> None:
        """
        Invalidate cache for a specific repository.

        Args:
            repo_url: Repository URL
        """
        cache_key = self._get_repo_cache_key(repo_url)
        metadata_path = self._get_metadata_path(cache_key)
        repo_path = self._get_repo_path(cache_key)

        # Remove metadata
        if metadata_path.exists():
            metadata_path.unlink()

        # Remove cached repository
        if repo_path.exists():
            shutil.rmtree(repo_path)

    def cleanup_expired(self) -> int:
        """
        Clean up all expired cache entries.

        Returns:
            Number of cache entries removed
        """
        removed = 0

        for metadata_path in self.metadata_dir.glob('*.json'):
            if not self._is_cache_valid(metadata_path):
                cache_key = metadata_path.stem
                repo_path = self._get_repo_path(cache_key)

                # Remove metadata
                metadata_path.unlink()

                # Remove cached repository
                if repo_path.exists():
                    shutil.rmtree(repo_path)

                removed += 1

        return removed

    def clear_all(self) -> None:
        """Clear all cache entries."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

        # Recreate directories
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_entries = 0
        valid_entries = 0
        expired_entries = 0
        total_size = 0

        for metadata_path in self.metadata_dir.glob('*.json'):
            total_entries += 1

            if self._is_cache_valid(metadata_path):
                valid_entries += 1
            else:
                expired_entries += 1

        # Calculate total cache size
        for item in self.cache_dir.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size

        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir),
            'expiry_hours': self.expiry_hours
        }


# Global cache instance
_cache_instance = None


def get_cache() -> RepositoryCache:
    """Get or create the global cache instance."""
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = RepositoryCache()

    return _cache_instance


# CLI for cache management
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Manage repository cache')
    parser.add_argument('action', choices=['stats', 'cleanup', 'clear'],
                       help='Action to perform')

    args = parser.parse_args()
    cache = get_cache()

    if args.action == 'stats':
        stats = cache.get_cache_stats()
        print("\n📊 Cache Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Valid entries: {stats['valid_entries']}")
        print(f"  Expired entries: {stats['expired_entries']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print(f"  Cache directory: {stats['cache_dir']}")
        print(f"  Expiry time: {stats['expiry_hours']} hours")

    elif args.action == 'cleanup':
        removed = cache.cleanup_expired()
        print(f"\n🧹 Cleaned up {removed} expired cache entries")

    elif args.action == 'clear':
        cache.clear_all()
        print("\n🗑️  Cleared all cache entries")
