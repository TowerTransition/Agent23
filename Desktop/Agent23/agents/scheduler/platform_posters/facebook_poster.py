"""
Facebook Poster - Module for posting content to Facebook Pages.

This module handles authentication via Meta Graph API, retrieves Page ID and access token,
and posts text/link/media content to Facebook Pages, enabling the SchedulerAgent to post
content to Facebook automatically.
"""

import os
import json
import logging
import time
import requests
from typing import Dict, List, Any, Optional, Union
import tempfile
import base64

class FacebookPoster:
    """
    Posts content to Facebook Pages using the Meta Graph API.
    
    Handles authentication, page access token retrieval, and posting text/link/media
    content to Facebook Pages.
    """
    
    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        user_access_token: Optional[str] = None,
        page_id: Optional[str] = None,
        page_access_token: Optional[str] = None,
        cache_dir: str = "cache",
        dry_run: bool = False
    ):
        """
        Initialize the FacebookPoster.
        
        Args:
            app_id: Facebook App ID
            app_secret: Facebook App Secret
            user_access_token: User access token (used to get page access token)
            page_id: Facebook Page ID (optional, will be retrieved if not provided)
            page_access_token: Page access token (optional, will be retrieved if not provided)
            cache_dir: Directory to cache API responses and tokens
            dry_run: If True, simulates posting without actually sending to API
        """
        self.logger = logging.getLogger(__name__)
        
        # Load API credentials from environment or parameters
        # Strip whitespace from all credentials to prevent "could not be decrypted" errors
        # Treat whitespace-only credentials as missing (None)
        
        # App ID and Secret
        app_id_raw = app_id or os.environ.get("FACEBOOK_APP_ID")
        if app_id_raw and app_id_raw.strip():
            self.app_id = app_id_raw.strip()
        else:
            self.app_id = None
        
        app_secret_raw = app_secret or os.environ.get("FACEBOOK_APP_SECRET")
        if app_secret_raw and app_secret_raw.strip():
            self.app_secret = app_secret_raw.strip()
        else:
            self.app_secret = None
        
        # User Access Token
        user_token = user_access_token or os.environ.get("FACEBOOK_USER_ACCESS_TOKEN")
        if user_token and user_token.strip():
            self.user_access_token = user_token.strip()
        else:
            self.user_access_token = None
        
        # Page ID
        page_id_raw = page_id or os.environ.get("FACEBOOK_PAGE_ID")
        if page_id_raw and page_id_raw.strip():
            self.page_id = page_id_raw.strip()
        else:
            self.page_id = None
        
        # Page Access Token
        page_token = page_access_token or os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
        if page_token and page_token.strip():
            self.page_access_token = page_token.strip()
        else:
            self.page_access_token = None
        
        # Configuration
        self.cache_dir = cache_dir
        self.dry_run = dry_run
        self.api_version = "v18.0"  # Using latest stable version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize page credentials if not in dry run mode
        if not dry_run:
            self._init_page_credentials()
        
        self.logger.info(
            "FacebookPoster initialized (dry_run: %s, page_id: %s)", 
            dry_run, self.page_id or "not set"
        )
    
    def _init_page_credentials(self) -> None:
        """
        Initialize or retrieve Page ID and Page access token.
        
        If page_id and page_access_token are not provided, this method will:
        1. Use the user access token to get a list of pages
        2. Retrieve the page access token for the first page (or specified page)
        3. Cache the credentials for future use
        """
        # If we already have both page_id and page_access_token, we're good
        if self.page_id and self.page_access_token:
            self.logger.info("Using provided Page ID and access token")
            return
        
        # If we have a cached page access token, try to use it
        cached_credentials = self._load_cached_credentials()
        if cached_credentials:
            self.page_id = cached_credentials.get("page_id") or self.page_id
            self.page_access_token = cached_credentials.get("page_access_token") or self.page_access_token
            if self.page_id and self.page_access_token:
                self.logger.info("Using cached Page credentials")
                return
        
        # Need user access token to get page credentials
        if not self.user_access_token:
            self.logger.warning(
                "No user access token provided. Cannot retrieve Page credentials. "
                "Please provide FACEBOOK_USER_ACCESS_TOKEN or FACEBOOK_PAGE_ACCESS_TOKEN"
            )
            return
        
        try:
            # Get pages that the user manages
            pages_url = f"{self.base_url}/me/accounts"
            params = {
                "access_token": self.user_access_token,
                "fields": "id,name,access_token"
            }
            
            response = requests.get(pages_url, params=params)
            
            if response.status_code != 200:
                error_data = response.json().get("error", {})
                error_msg = error_data.get("message", "Unknown error")
                self.logger.error("Error fetching pages: %s", error_msg)
                return
            
            pages_data = response.json()
            pages = pages_data.get("data", [])
            
            if not pages:
                self.logger.error("No pages found for this user access token")
                return
            
            # If page_id is specified, find that page
            if self.page_id:
                target_page = next(
                    (page for page in pages if page.get("id") == self.page_id),
                    None
                )
                if not target_page:
                    self.logger.error("Specified page_id not found in user's pages")
                    return
            else:
                # Use the first page
                target_page = pages[0]
                self.page_id = target_page.get("id")
            
            # Get the page access token
            self.page_access_token = target_page.get("access_token")
            
            if not self.page_access_token:
                self.logger.error("No access token found for page")
                return
            
            # Cache the credentials
            self._cache_credentials({
                "page_id": self.page_id,
                "page_access_token": self.page_access_token
            })
            
            self.logger.info(
                "Successfully retrieved Page credentials: page_id=%s, page_name=%s",
                self.page_id, target_page.get("name", "Unknown")
            )
            
        except Exception as e:
            self.logger.error("Error initializing page credentials: %s", str(e))
    
    def _load_cached_credentials(self) -> Optional[Dict[str, str]]:
        """Load cached page credentials from file."""
        cache_file = os.path.join(self.cache_dir, "facebook_page_credentials.json")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning("Error loading cached credentials: %s", str(e))
            return None
    
    def _cache_credentials(self, credentials: Dict[str, str]) -> None:
        """Cache page credentials to file."""
        cache_file = os.path.join(self.cache_dir, "facebook_page_credentials.json")
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(credentials, f, indent=2)
        except Exception as e:
            self.logger.error("Error caching credentials: %s", str(e))
    
    def post(self, content: Dict[str, Any], post_id: str) -> Dict[str, Any]:
        """
        Post content to Facebook Page.
        
        Args:
            content: Dictionary containing the content to post
                - text: Text content (required)
                - link: Optional URL to share
                - image: Optional image data (dict with filepath, url, or base64)
            post_id: Unique ID for this post
            
        Returns:
            Dictionary with the post result
        """
        if self.dry_run:
            return self._simulate_post(content, post_id)
        
        if not self.page_id or not self.page_access_token:
            return {
                "success": False,
                "error": "Facebook Page ID and access token not available",
                "post_id": post_id
            }
        
        # Extract content
        text = content.get("text", "")
        link = content.get("link")
        has_image = "image" in content
        
        try:
            # Determine post type and call appropriate method
            if has_image:
                return self._post_with_image(text, content["image"], link, post_id)
            elif link:
                return self._post_with_link(text, link, post_id)
            else:
                return self._post_text_only(text, post_id)
                
        except Exception as e:
            error_msg = str(e)
            self.logger.error("Error posting to Facebook: %s", error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "post_id": post_id
            }
    
    def _post_text_only(self, text: str, post_id: str) -> Dict[str, Any]:
        """
        Post text-only content to Facebook.
        
        Args:
            text: Text content to post
            post_id: Unique ID for this post
            
        Returns:
            Dictionary with the post result
        """
        url = f"{self.base_url}/{self.page_id}/feed"
        
        params = {
            "access_token": self.page_access_token,
            "message": text
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code != 200:
            error_data = response.json().get("error", {})
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            self.logger.error("Error posting to Facebook: %s", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "post_id": post_id
            }
        
        post_data = response.json()
        facebook_post_id = post_data.get("id", "")
        
        # Extract post ID from the response (format: {page_id}_{post_id})
        if "_" in facebook_post_id:
            actual_post_id = facebook_post_id.split("_")[-1]
        else:
            actual_post_id = facebook_post_id
        
        post_url = f"https://www.facebook.com/{self.page_id}/posts/{actual_post_id}"
        
        self.logger.info("Facebook post published successfully: %s", post_url)
        
        # Cache the response
        self._cache_response(post_id, {
            "facebook_post_id": facebook_post_id,
            "post_url": post_url,
            "timestamp": time.time()
        })
        
        return {
            "success": True,
            "facebook_post_id": facebook_post_id,
            "post_url": post_url,
            "post_id": post_id
        }
    
    def _post_with_link(self, text: str, link: str, post_id: str) -> Dict[str, Any]:
        """
        Post content with a link to Facebook.
        
        Args:
            text: Text content to post
            link: URL to share
            post_id: Unique ID for this post
            
        Returns:
            Dictionary with the post result
        """
        url = f"{self.base_url}/{self.page_id}/feed"
        
        params = {
            "access_token": self.page_access_token,
            "message": text,
            "link": link
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code != 200:
            error_data = response.json().get("error", {})
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            self.logger.error("Error posting link to Facebook: %s", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "post_id": post_id
            }
        
        post_data = response.json()
        facebook_post_id = post_data.get("id", "")
        
        # Extract post ID
        if "_" in facebook_post_id:
            actual_post_id = facebook_post_id.split("_")[-1]
        else:
            actual_post_id = facebook_post_id
        
        post_url = f"https://www.facebook.com/{self.page_id}/posts/{actual_post_id}"
        
        self.logger.info("Facebook post with link published successfully: %s", post_url)
        
        # Cache the response
        self._cache_response(post_id, {
            "facebook_post_id": facebook_post_id,
            "post_url": post_url,
            "link": link,
            "timestamp": time.time()
        })
        
        return {
            "success": True,
            "facebook_post_id": facebook_post_id,
            "post_url": post_url,
            "post_id": post_id
        }
    
    def _post_with_image(self, text: str, image_data: Dict[str, Any], link: Optional[str], post_id: str) -> Dict[str, Any]:
        """
        Post content with an image to Facebook.
        
        Args:
            text: Text content to post
            image_data: Dictionary containing image information
            link: Optional URL to share with the image
            post_id: Unique ID for this post
            
        Returns:
            Dictionary with the post result
        """
        # First, upload the image
        image_url = self._upload_image(image_data)
        if not image_url:
            return {
                "success": False,
                "error": "Failed to upload image to Facebook",
                "post_id": post_id
            }
        
        # Post with the uploaded image
        url = f"{self.base_url}/{self.page_id}/photos"
        
        params = {
            "access_token": self.page_access_token,
            "url": image_url,
            "message": text
        }
        
        # If there's a link, we'll post it as a separate feed post after the photo
        response = requests.post(url, params=params)
        
        if response.status_code != 200:
            error_data = response.json().get("error", {})
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            self.logger.error("Error posting image to Facebook: %s", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "post_id": post_id
            }
        
        photo_data = response.json()
        photo_id = photo_data.get("id", "")
        photo_post_id = photo_data.get("post_id", "")
        
        # If there's a link, create a separate feed post with the link
        if link:
            link_post_result = self._post_with_link(text, link, f"{post_id}_link")
            # We'll return the photo post result, but note the link was posted separately
        
        # Extract post ID
        if "_" in photo_post_id:
            actual_post_id = photo_post_id.split("_")[-1]
        else:
            actual_post_id = photo_post_id or photo_id
        
        post_url = f"https://www.facebook.com/{self.page_id}/posts/{actual_post_id}"
        
        self.logger.info("Facebook post with image published successfully: %s", post_url)
        
        # Cache the response
        self._cache_response(post_id, {
            "facebook_post_id": photo_post_id or photo_id,
            "photo_id": photo_id,
            "post_url": post_url,
            "timestamp": time.time()
        })
        
        return {
            "success": True,
            "facebook_post_id": photo_post_id or photo_id,
            "photo_id": photo_id,
            "post_url": post_url,
            "post_id": post_id
        }
    
    def _upload_image(self, image_data: Dict[str, Any]) -> Optional[str]:
        """
        Upload an image to Facebook and return a URL.
        
        For Facebook Graph API, we can either:
        1. Use an existing public URL
        2. Upload the image to a temporary hosting service first
        
        Args:
            image_data: Dictionary containing image information
            
        Returns:
            Public URL for the image if successful, None otherwise
        """
        # If the image already has a URL, use it
        if "url" in image_data:
            return image_data["url"]
        
        # For filepath or base64, we need to upload to a temporary hosting service
        # For now, we'll use a simple approach: upload directly to Facebook's API
        # Note: Facebook's photo upload endpoint accepts multipart/form-data
        
        # Get image filepath
        image_path = self._get_image_filepath(image_data)
        if not image_path:
            self.logger.error("No valid image data found for upload")
            return None
        
        try:
            # Upload image to Facebook as a temporary photo
            # This creates a photo that can be referenced
            upload_url = f"{self.base_url}/{self.page_id}/photos"
            
            with open(image_path, 'rb') as image_file:
                files = {
                    'source': image_file
                }
                params = {
                    "access_token": self.page_access_token,
                    "published": "false"  # Upload but don't publish yet
                }
                
                response = requests.post(upload_url, files=files, params=params)
                
                if response.status_code == 200:
                    photo_data = response.json()
                    photo_id = photo_data.get("id", "")
                    
                    # Get the photo URL
                    photo_info_url = f"{self.base_url}/{photo_id}"
                    photo_info_params = {
                        "access_token": self.page_access_token,
                        "fields": "images"
                    }
                    
                    photo_info_response = requests.get(photo_info_url, params=photo_info_params)
                    if photo_info_response.status_code == 200:
                        photo_info = photo_info_response.json()
                        images = photo_info.get("images", [])
                        if images:
                            # Get the largest image URL
                            image_url = max(images, key=lambda x: x.get("width", 0)).get("source")
                            return image_url
                    
                    # Fallback: construct URL from photo ID
                    return f"https://graph.facebook.com/{self.api_version}/{photo_id}/picture"
            
            self.logger.error("Failed to upload image to Facebook")
            return None
            
        except Exception as e:
            self.logger.error("Error uploading image: %s", str(e))
            return None
        finally:
            # Clean up temporary file if needed
            if image_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(image_path)
                except Exception as e:
                    self.logger.warning("Could not remove temporary file: %s", str(e))
    
    def _get_image_filepath(self, image_data: Dict[str, Any]) -> Optional[str]:
        """
        Get or create a filepath for an image.
        
        Args:
            image_data: Dictionary containing image information
            
        Returns:
            Filepath for the image if successful, None otherwise
        """
        # Check if we have a file path
        if "filepath" in image_data and os.path.exists(image_data["filepath"]):
            return image_data["filepath"]
        
        # Check if we have base64 data
        elif "base64" in image_data:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_path = temp_file.name
                # Write base64 data to file
                temp_file.write(base64.b64decode(image_data["base64"]))
            
            return temp_path
        
        self.logger.error("No valid image data found")
        return None
    
    def _simulate_post(self, content: Dict[str, Any], post_id: str) -> Dict[str, Any]:
        """
        Simulate posting to Facebook without actually sending API requests.
        
        Args:
            content: Dictionary containing the content to post
            post_id: Unique ID for this post
            
        Returns:
            Dictionary with the simulated post result
        """
        text = content.get("text", "")
        has_image = "image" in content
        has_link = "link" in content
        
        self.logger.info(
            "[DRY RUN] Would post to Facebook: %s%s%s",
            text[:50] + "..." if len(text) > 50 else text,
            " (with image)" if has_image else "",
            " (with link)" if has_link else ""
        )
        
        # Simulate a post ID and URL
        timestamp = int(time.time())
        facebook_post_id = f"{self.page_id or 'page'}_{timestamp}_{post_id[-8:]}"
        post_url = f"https://www.facebook.com/{self.page_id or 'page'}/posts/{timestamp}"
        
        return {
            "success": True,
            "facebook_post_id": facebook_post_id,
            "post_url": post_url,
            "post_id": post_id,
            "simulated": True
        }
    
    def _cache_response(self, post_id: str, response_data: Dict[str, Any]) -> None:
        """
        Cache the API response for a post.
        
        Args:
            post_id: Unique ID for the post
            response_data: Data to cache
        """
        cache_file = os.path.join(self.cache_dir, f"facebook_{post_id}.json")
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(response_data, f, indent=2)
        except Exception as e:
            self.logger.error("Error caching Facebook response: %s", str(e))


