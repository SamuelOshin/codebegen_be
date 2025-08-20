#!/usr/bin/env python3
"""
Comprehensive Code Generation Pipeline Test
Tests the complete flow from authentication to file generation
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional

class CodeGenerationPipelineTest:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.project_id = None
        self.generation_id = None
        self.results = {
            "test_start_time": datetime.now().isoformat(),
            "steps": {},
            "file_outputs": {},
            "errors": []
        }
    
    def log_step(self, step_name: str, success: bool, details: Dict[str, Any]):
        """Log a test step"""
        self.results["steps"][step_name] = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        print(f"{'✅' if success else '❌'} {step_name}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def test_server_health(self) -> bool:
        """Test if server is running and healthy"""
        try:
            response = self.session.get(f"{self.base_url}/docs", timeout=10)
            success = response.status_code == 200
            self.log_step("Server Health Check", success, {
                "status_code": response.status_code,
                "response_size": len(response.content)
            })
            return success
        except Exception as e:
            self.log_step("Server Health Check", False, {"error": str(e)})
            return False
    
    def test_user_creation(self) -> bool:
        """Create or verify test user exists"""
        try:
            # Try to create a test user
            user_data = {
                "username": "pipeline_test_user",
                "email": "test@codebegen.com",
                "password": "testpassword123",
                "full_name": "Pipeline Test User"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=user_data)
            
            if response.status_code == 201:
                user_info = response.json()
                self.user_id = user_info.get("id")
                success = True
                details = {"message": "User created successfully", "user_id": self.user_id}
            elif response.status_code == 400 and "already exists" in response.text:
                success = True
                details = {"message": "User already exists, proceeding"}
            else:
                success = False
                details = {"error": f"Status {response.status_code}: {response.text}"}
            
            self.log_step("User Creation/Verification", success, details)
            return success
            
        except Exception as e:
            self.log_step("User Creation/Verification", False, {"error": str(e)})
            return False
    
    def test_authentication(self) -> bool:
        """Test user login and token generation"""
        try:
            login_data = {
                "username": "pipeline_test_user",
                "password": "testpassword123"
            }
            
            # Try form data first
            response = self.session.post(f"{self.base_url}/auth/login", data=login_data)
            
            if response.status_code != 200:
                # Try JSON format
                response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.auth_token = auth_data.get("access_token")
                self.user_id = auth_data.get("user_id") or self.user_id
                
                # Set authorization header for future requests
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                
                success = True
                details = {
                    "token_received": bool(self.auth_token),
                    "token_length": len(self.auth_token) if self.auth_token else 0,
                    "user_id": self.user_id
                }
            else:
                success = False
                details = {"status_code": response.status_code, "response": response.text}
            
            self.log_step("Authentication", success, details)
            return success
            
        except Exception as e:
            self.log_step("Authentication", False, {"error": str(e)})
            return False
    
    def test_project_creation(self) -> bool:
        """Create a test project for code generation"""
        try:
            project_data = {
                "name": "Pipeline Test Project",
                "description": "Test project for code generation pipeline validation",
                "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
                "project_type": "api",
                "domain": "ecommerce"
            }
            
            response = self.session.post(f"{self.base_url}/projects/", json=project_data)
            
            if response.status_code == 201:
                project_info = response.json()
                self.project_id = project_info.get("id")
                success = True
                details = {
                    "project_id": self.project_id,
                    "project_name": project_info.get("name"),
                    "tech_stack": project_info.get("tech_stack")
                }
            else:
                success = False
                details = {"status_code": response.status_code, "response": response.text}
            
            self.log_step("Project Creation", success, details)
            return success
            
        except Exception as e:
            self.log_step("Project Creation", False, {"error": str(e)})
            return False
    
    def test_generation_request(self) -> bool:
        """Submit a code generation request"""
        try:
            generation_data = {
                "prompt": "Create a FastAPI e-commerce application with user authentication, product catalog, shopping cart, and order management. Include proper error handling, validation, and database models.",
                "project_id": self.project_id,
                "context": {
                    "target_framework": "FastAPI",
                    "database": "PostgreSQL",
                    "authentication": "JWT",
                    "features": ["user_auth", "product_catalog", "shopping_cart", "orders"]
                },
                "is_iteration": False
            }
            
            response = self.session.post(f"{self.base_url}/generations/", json=generation_data)
            
            if response.status_code == 201:
                generation_info = response.json()
                self.generation_id = generation_info.get("id")
                success = True
                details = {
                    "generation_id": self.generation_id,
                    "status": generation_info.get("status"),
                    "prompt_length": len(generation_data["prompt"])
                }
            else:
                success = False
                details = {"status_code": response.status_code, "response": response.text}
            
            self.log_step("Generation Request", success, details)
            return success
            
        except Exception as e:
            self.log_step("Generation Request", False, {"error": str(e)})
            return False
    
    def test_generation_monitoring(self, max_wait_minutes: int = 5) -> bool:
        """Monitor generation progress"""
        try:
            if not self.generation_id:
                self.log_step("Generation Monitoring", False, {"error": "No generation ID available"})
                return False
            
            start_time = time.time()
            max_wait_seconds = max_wait_minutes * 60
            last_status = None
            
            while time.time() - start_time < max_wait_seconds:
                response = self.session.get(f"{self.base_url}/generations/{self.generation_id}")
                
                if response.status_code == 200:
                    generation_info = response.json()
                    current_status = generation_info.get("status")
                    
                    if current_status != last_status:
                        print(f"   Status update: {current_status}")
                        last_status = current_status
                    
                    if current_status in ["completed", "failed", "cancelled"]:
                        success = current_status == "completed"
                        details = {
                            "final_status": current_status,
                            "total_time": generation_info.get("total_time"),
                            "quality_score": generation_info.get("quality_score"),
                            "error_message": generation_info.get("error_message")
                        }
                        self.log_step("Generation Monitoring", success, details)
                        return success
                
                time.sleep(10)  # Check every 10 seconds
            
            # Timeout reached
            self.log_step("Generation Monitoring", False, {
                "error": f"Timeout after {max_wait_minutes} minutes",
                "last_status": last_status
            })
            return False
            
        except Exception as e:
            self.log_step("Generation Monitoring", False, {"error": str(e)})
            return False
    
    def test_file_outputs(self) -> bool:
        """Check generated file outputs"""
        try:
            if not self.generation_id:
                self.log_step("File Output Check", False, {"error": "No generation ID available"})
                return False
            
            response = self.session.get(f"{self.base_url}/generations/{self.generation_id}/files")
            
            if response.status_code == 200:
                files_data = response.json()
                files = files_data.get("files", {})
                
                success = len(files) > 0
                details = {
                    "files_count": len(files),
                    "file_names": list(files.keys())[:10],  # Show first 10 files
                    "total_files": len(files)
                }
                
                # Store file outputs in results
                self.results["file_outputs"] = files
                
            else:
                success = False
                details = {"status_code": response.status_code, "response": response.text}
            
            self.log_step("File Output Check", success, details)
            return success
            
        except Exception as e:
            self.log_step("File Output Check", False, {"error": str(e)})
            return False
    
    def test_download_functionality(self) -> bool:
        """Test ZIP download functionality"""
        try:
            if not self.generation_id:
                self.log_step("Download Test", False, {"error": "No generation ID available"})
                return False
            
            response = self.session.get(f"{self.base_url}/generations/{self.generation_id}/download")
            
            if response.status_code == 200:
                # Save the ZIP file
                zip_filename = f"generated_project_{self.generation_id}.zip"
                with open(zip_filename, "wb") as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                success = file_size > 0
                details = {
                    "zip_file": zip_filename,
                    "file_size_bytes": file_size,
                    "content_type": response.headers.get("content-type")
                }
                
                # Add download info to results
                self.results["download"] = {
                    "filename": zip_filename,
                    "size": file_size,
                    "path": os.path.abspath(zip_filename)
                }
                
            else:
                success = False
                details = {"status_code": response.status_code, "response": response.text}
            
            self.log_step("Download Test", success, details)
            return success
            
        except Exception as e:
            self.log_step("Download Test", False, {"error": str(e)})
            return False
    
    def generate_final_report(self):
        """Generate comprehensive test report"""
        self.results["test_end_time"] = datetime.now().isoformat()
        
        # Count successes
        total_steps = len(self.results["steps"])
        successful_steps = sum(1 for step in self.results["steps"].values() if step["success"])
        
        self.results["summary"] = {
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "success_rate": f"{(successful_steps/total_steps)*100:.1f}%" if total_steps > 0 else "0%",
            "generation_id": self.generation_id,
            "project_id": self.project_id
        }
        
        # Save detailed report
        report_filename = f"pipeline_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n🎉 Pipeline Test Complete!")
        print(f"📊 Success Rate: {self.results['summary']['success_rate']}")
        print(f"📁 Report saved: {report_filename}")
        
        if self.results.get("download"):
            print(f"💾 Generated project ZIP: {self.results['download']['filename']}")
        
        return report_filename

def main():
    """Run the complete pipeline test"""
    print("🚀 Starting Complete Code Generation Pipeline Test\n")
    
    tester = CodeGenerationPipelineTest()
    
    # Run all tests in sequence
    tests = [
        tester.test_server_health,
        tester.test_user_creation,
        tester.test_authentication,
        tester.test_project_creation,
        tester.test_generation_request,
        tester.test_generation_monitoring,
        tester.test_file_outputs,
        tester.test_download_functionality
    ]
    
    for test in tests:
        if not test():
            print(f"\n❌ Test failed: {test.__name__}")
            print("Continuing with remaining tests...\n")
    
    # Generate final report
    report_file = tester.generate_final_report()
    
    return tester.results

if __name__ == "__main__":
    results = main()
