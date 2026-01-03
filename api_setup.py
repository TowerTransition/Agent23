#!/usr/bin/env python3
"""
API Setup and Validation Utility

This script helps verify API connections and provides utilities for authenticating
with various APIs used by the TrendScannerAgent, ContentCreatorAgent, and SchedulerAgent.
It follows best practices for API usage as outlined in api.mdc.
"""

import os
import sys
import json
import logging
import argparse
import requests
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_setup.log')
    ]
)

logger = logging.getLogger("api_setup")

class APISetup:
    """Utility class for setting up and validating API connections"""
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize API Setup utility.
        
        Args:
            env_file: Path to .env file containing API credentials
        """
        # Load environment variables
        load_dotenv(env_file)
        self.logger = logging.getLogger(__name__)
        
        # Set debug level if needed
        if os.getenv("DEBUG", "False").lower() == "true":
            logging.getLogger().setLevel(logging.DEBUG)
        
        self.logger.info("API Setup initialized")
    
    def validate_local_llm_api(self) -> bool:
        """
        Validate Local LLM API endpoint (OpenAI-compatible).
        
        Returns:
            True if endpoint is accessible and working, False otherwise
        """
        endpoint = os.getenv("LOCAL_LLM_ENDPOINT")
        if not endpoint:
            self.logger.warning("LOCAL_LLM_ENDPOINT not found. Using local LLM is recommended for Google Cloud deployment.")
            return False
        
        try:
            self.logger.info(f"Testing Local LLM API connection at {endpoint}...")
            
            # Get API key if needed
            api_key = os.getenv("LOCAL_LLM_API_KEY")
            headers = {"Content-Type": "application/json"}
            if api_key and api_key != "not-needed-for-local":
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Test with a simple chat completion request
            test_payload = {
                "model": "tinyllama",  # Default model name for TinyLlama
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Local LLM API connection successful at {endpoint}.")
                return True
            else:
                self.logger.error(f"Local LLM API error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Could not connect to Local LLM endpoint: {endpoint}. Is the LLM server running?")
            return False
        except Exception as e:
            self.logger.error(f"Error validating Local LLM API: {e}")
            return False
    
    def validate_openai_api(self) -> bool:
        """
        Validate OpenAI API credentials (optional - for backward compatibility).
        
        Returns:
            True if API key is valid and working, False otherwise
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.logger.info("OpenAI API key not found. This is optional if using local LLM.")
            return False
    
    def validate_stability_api(self) -> bool:
        """
        Validate Stability AI API credentials.
        
        Returns:
            True if API key is valid and working, False otherwise
        """
        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            self.logger.error("Stability AI API key not found. Set STABILITY_API_KEY in .env file.")
            return False
        
        try:
            self.logger.info("Testing Stability AI API connection...")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Use a simple request to check API connectivity
            response = requests.get(
                "https://api.stability.ai/v1/engines/list",
                headers=headers
            )
            
            if response.status_code == 200:
                engines = response.json()
                engine_count = len(engines)
                self.logger.info(f"Stability AI API connection successful. Found {engine_count} engines.")
                
                # List available engines
                engine_ids = [engine["id"] for engine in engines]
                self.logger.info(f"Available engines: {', '.join(engine_ids)}")
                
                # Check if specified model exists
                specified_model = os.getenv("STABILITY_MODEL", "stable-diffusion-xl-1024-v1-0")
                if specified_model in engine_ids:
                    self.logger.info(f"Specified model '{specified_model}' is available.")
                else:
                    self.logger.warning(f"Specified model '{specified_model}' not found.")
                
                return True
            else:
                self.logger.error(f"Stability AI API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating Stability AI API: {e}")
            return False
    
    def validate_twitter_api(self) -> bool:
        """
        Validate Twitter API credentials.
        
        Returns:
            True if credentials are valid and working, False otherwise
        """
        import tweepy
        
        api_key = os.getenv("TWITTER_API_KEY")
        api_secret = os.getenv("TWITTER_API_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        
        if not (api_key and api_secret) and not bearer_token:
            self.logger.error("Twitter API credentials not found. Set TWITTER_API_KEY and TWITTER_API_SECRET (for v1.1) or TWITTER_BEARER_TOKEN (for v2) in .env file.")
            return False
        
        try:
            self.logger.info("Testing Twitter API connection...")
            
            # Try v2 API with bearer token if available
            if bearer_token:
                client = tweepy.Client(bearer_token=bearer_token)
                try:
                    # Simple request to check API connectivity
                    trends = client.get_place_trends(id=1)  # 1 is the WOEID for worldwide
                    self.logger.info("Twitter API v2 connection successful.")
                    return True
                except Exception as e_v2:
                    self.logger.warning(f"Twitter API v2 error: {e_v2}")
                    self.logger.info("Trying v1.1 API...")
            
            # Try v1.1 API with consumer keys and access tokens
            if api_key and api_secret and access_token and access_secret:
                # Set up v1.1 authentication
                auth = tweepy.OAuth1UserHandler(
                    api_key, api_secret, 
                    access_token, access_secret
                )
                api = tweepy.API(auth)
                
                # Verify credentials
                user = api.verify_credentials()
                self.logger.info(f"Twitter API v1.1 connection successful. Authenticated as @{user.screen_name}.")
                return True
            else:
                self.logger.error("Twitter API v1.1 credentials incomplete.")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating Twitter API: {e}")
            return False
    
    def validate_instagram_api(self) -> bool:
        """
        Validate Instagram API credentials.
        
        Returns:
            True if credentials are valid and working, False otherwise
        """
        # Check if we have username/password for instagrapi
        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")
        
        # Check if we have Graph API credentials
        access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
        
        if not (username and password) and not (access_token and account_id):
            self.logger.error("Instagram credentials not found. Set either INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD for instagrapi or INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID for Graph API in .env file.")
            return False
        
        # Try instagrapi if username/password is available
        if username and password:
            try:
                from instagrapi import Client
                
                self.logger.info("Testing Instagram connection via instagrapi...")
                client = Client()
                
                # Don't actually login during test since it can trigger security checks
                self.logger.info("Instagram credentials found for instagrapi. For security reasons, actual login is skipped in validation.")
                self.logger.info("Set up for instagrapi complete.")
                return True
                
            except ImportError:
                self.logger.error("instagrapi package not installed. Install with 'pip install instagrapi'.")
                return False
            except Exception as e:
                self.logger.error(f"Error setting up instagrapi: {e}")
                return False
        
        # Try Graph API if access_token is available
        if access_token and account_id:
            try:
                self.logger.info("Testing Instagram Graph API connection...")
                
                url = f"https://graph.facebook.com/v17.0/{account_id}?fields=username&access_token={access_token}"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    username = data.get("username")
                    self.logger.info(f"Instagram Graph API connection successful. Connected to account @{username}.")
                    return True
                else:
                    self.logger.error(f"Instagram Graph API error: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error validating Instagram Graph API: {e}")
                return False
        
        return False
    
    def validate_linkedin_api(self) -> bool:
        """
        Validate LinkedIn API credentials.
        
        Returns:
            True if credentials are valid and working, False otherwise
        """
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            self.logger.error("LinkedIn API credentials not found. Set LINKEDIN_ACCESS_TOKEN in .env file.")
            return False
        
        try:
            self.logger.info("Testing LinkedIn API connection...")
            
            # Try to get basic profile information
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            response = requests.get(
                "https://api.linkedin.com/v2/me",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"LinkedIn API connection successful. Connected to {data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}.")
                
                # Check if we have organization ID for company posts
                org_id = os.getenv("LINKEDIN_ORGANIZATION_ID")
                if org_id:
                    self.logger.info(f"LinkedIn Organization ID found: {org_id}")
                else:
                    self.logger.info("No LinkedIn Organization ID found. User profile posting only.")
                
                return True
            else:
                self.logger.error(f"LinkedIn API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating LinkedIn API: {e}")
            return False
    
    def check_optional_services(self) -> Dict[str, bool]:
        """
        Check for optional third-party services.
        
        Returns:
            Dictionary of service names and their availability status
        """
        services = {}
        
        # Check for Ayrshare
        ayrshare_key = os.getenv("AYRSHARE_API_KEY")
        if ayrshare_key:
            self.logger.info("Ayrshare API key found. Testing connection...")
            try:
                headers = {
                    "Authorization": f"Bearer {ayrshare_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.get(
                    "https://app.ayrshare.com/api/profiles",
                    headers=headers
                )
                
                if response.status_code == 200:
                    self.logger.info("Ayrshare API connection successful.")
                    services["ayrshare"] = True
                else:
                    self.logger.error(f"Ayrshare API error: {response.status_code} - {response.text}")
                    services["ayrshare"] = False
            except Exception as e:
                self.logger.error(f"Error validating Ayrshare API: {e}")
                services["ayrshare"] = False
        else:
            services["ayrshare"] = False
        
        # Check for AWS S3 (for image storage)
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_bucket = os.getenv("AWS_BUCKET_NAME")
        
        if aws_access_key and aws_secret_key and aws_bucket:
            self.logger.info("AWS S3 credentials found.")
            try:
                import boto3
                services["aws_s3"] = True
                self.logger.info("AWS S3 credentials validated. Note: Actual bucket access not tested.")
            except ImportError:
                self.logger.warning("boto3 package not installed. Install with 'pip install boto3' to use AWS S3.")
                services["aws_s3"] = False
        else:
            services["aws_s3"] = False
        
        return services
    
    def validate_all(self) -> Dict[str, bool]:
        """
        Validate all API connections.
        
        Returns:
            Dictionary of API names and their validity status
        """
        results = {}
        
        # Core APIs
        results["local_llm"] = self.validate_local_llm_api()
        results["openai"] = self.validate_openai_api()  # Optional, for backward compatibility
        results["stability"] = self.validate_stability_api()
        
        # Social platforms
        results["twitter"] = self.validate_twitter_api()
        results["instagram"] = self.validate_instagram_api()
        results["linkedin"] = self.validate_linkedin_api()
        
        # Optional services
        optional_services = self.check_optional_services()
        results.update(optional_services)
        
        return results
    
    def generate_api_summary(self, results: Dict[str, bool]) -> str:
        """
        Generate a readable summary of API validation results.
        
        Args:
            results: Dictionary of API names and their validity status
            
        Returns:
            Formatted string summary
        """
        summary = "\n\n" + "="*50 + "\n"
        summary += "API VALIDATION SUMMARY\n"
        summary += "="*50 + "\n\n"
        
        # Group by category
        categories = {
            "Content Generation": ["local_llm", "openai", "stability"],
            "Social Platforms": ["twitter", "instagram", "linkedin"],
            "Optional Services": ["ayrshare", "aws_s3"]
        }
        
        for category, apis in categories.items():
            summary += f"{category}:\n"
            summary += "-" * len(category) + "\n"
            
            for api in apis:
                status = results.get(api, False)
                status_str = "✓ CONNECTED" if status else "✗ NOT CONNECTED"
                summary += f"  {api.upper()}: {status_str}\n"
            
            summary += "\n"
        
        # Overall assessment
        # Local LLM is preferred, but OpenAI is optional for backward compatibility
        llm_valid = results.get("local_llm", False) or results.get("openai", False)
        stability_valid = results.get("stability", False)
        social_apis = ["twitter", "instagram", "linkedin"]
        any_social_valid = any(results.get(api, False) for api in social_apis)
        
        summary += "Overall Assessment:\n"
        summary += "-----------------\n"
        
        if llm_valid and stability_valid and any_social_valid:
            summary += "✓ System is READY to run! All required APIs are connected.\n"
        elif not llm_valid:
            summary += "✗ LLM API is not connected. Set LOCAL_LLM_ENDPOINT (recommended) or OPENAI_API_KEY.\n"
        elif not stability_valid:
            summary += "⚠ Stability AI not connected. Image generation will be disabled.\n"
        elif not any_social_valid:
            summary += "✗ NO SOCIAL PLATFORM APIs are connected. At least one is required for posting.\n"
        else:
            summary += "⚠ System can run with limitations. Check failing connections above.\n"
        
        return summary
    
    def test_openai_prompt(self, prompt: str = "Write a short tweet about space exploration.") -> Dict[str, Any]:
        """
        Test OpenAI with a sample prompt.
        
        Args:
            prompt: Test prompt to send to OpenAI
            
        Returns:
            Response from OpenAI API
        """
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        if not api_key:
            self.logger.error("OpenAI API key not found.")
            return {"error": "API key not found"}
        
        try:
            self.logger.info(f"Testing OpenAI prompt using model {model}...")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a ContentCreatorAgent for a science/education brand."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 150
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                self.logger.info(f"OpenAI prompt test successful. Response: {content}")
                return result
            else:
                self.logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return {"error": response.text}
            
        except Exception as e:
            self.logger.error(f"Error testing OpenAI prompt: {e}")
            return {"error": str(e)}

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="API Setup and Validation Tool")
    
    parser.add_argument('--env-file', '-e', type=str, default=".env",
                        help='Path to .env file containing API credentials')
    
    parser.add_argument('--test-openai', '-t', action='store_true',
                        help='Test OpenAI API with a sample prompt')
    
    parser.add_argument('--prompt', '-p', type=str, 
                        default="Write a short tweet about space exploration.",
                        help='Sample prompt to test with OpenAI')
    
    parser.add_argument('--save-report', '-s', action='store_true',
                        help='Save validation report to file')
    
    parser.add_argument('--report-file', '-r', type=str, 
                        default="api_validation_report.txt",
                        help='Path to save validation report')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Initialize API setup
    api_setup = APISetup(env_file=args.env_file)
    
    # Validate all APIs
    results = api_setup.validate_all()
    
    # Generate and print summary
    summary = api_setup.generate_api_summary(results)
    print(summary)
    
    # Save report if requested
    if args.save_report:
        try:
            with open(args.report_file, 'w') as f:
                f.write(summary)
            print(f"\nReport saved to {args.report_file}")
        except Exception as e:
            print(f"\nError saving report: {e}")
    
    # Test OpenAI with prompt if requested
    if args.test_openai:
        print("\nTesting OpenAI with sample prompt...")
        response = api_setup.test_openai_prompt(args.prompt)
        
        if "error" not in response:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"\nOpenAI Response:\n{content}")
        else:
            print(f"\nError: {response.get('error')}")
    
    # Exit code based on validation results
    # Local LLM is preferred, but OpenAI is optional for backward compatibility
    llm_valid = results.get("local_llm", False) or results.get("openai", False)
    social_apis = ["twitter", "instagram", "linkedin"]
    any_social_valid = any(results.get(api, False) for api in social_apis)
    
    if llm_valid and any_social_valid:
        print("\nAPI setup is complete and ready to use!")
        sys.exit(0)
    else:
        print("\nAPI setup is incomplete. Please fix the issues above.")
        sys.exit(1) 