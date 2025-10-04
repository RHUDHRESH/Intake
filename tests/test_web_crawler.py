"""
Tests for Web Crawler Agent
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from agents.web_crawler.agent import WebCrawlerAgent
from utils.base_agent import AgentInput

class TestWebCrawlerAgent:
    """Test cases for WebCrawlerAgent"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            "headless": True,
            "timeout": 30000,
            "max_pages": 5,
            "requires_web_scraping": True
        }

    @pytest.fixture
    def agent(self, config):
        """Create WebCrawlerAgent instance"""
        return WebCrawlerAgent(config)

    @pytest.fixture
    def sample_input(self):
        """Sample input for testing"""
        return AgentInput(
            request_id="test-request-123",
            input_data={
                "website": "https://example.com",
                "campaign_name": "Test Campaign",
                "description": "This is a test campaign for dentists"
            }
        )

    def test_agent_initialization(self, config):
        """Test agent initialization"""
        agent = WebCrawlerAgent(config)

        assert agent.agent_name == "WebCrawlerAgent"
        assert agent.get_dependencies() == []
        assert agent.requires_web_scraping() == True
        assert agent.get_config_value("timeout") == 30000

    def test_url_extraction(self, agent):
        """Test URL extraction from text"""
        text = "Check out our website at https://example.com and also visit https://test.org for more info"
        urls = agent.extract_urls_from_text(text)

        assert "https://example.com" in urls
        assert "https://test.org" in urls
        assert len(urls) == 2

    def test_keyword_extraction(self, agent):
        """Test keyword extraction"""
        text = "This is a great product for dentists and doctors who need marketing help"
        keywords = agent.extract_keywords(text, max_keywords=5)

        assert "product" in keywords
        assert "dentists" in keywords
        assert "doctors" in keywords
        assert "marketing" in keywords

    def test_sentiment_analysis(self, agent):
        """Test basic sentiment analysis"""
        positive_text = "This is great and amazing product"
        negative_text = "This is terrible and awful"

        positive_sentiment = agent.analyze_sentiment(positive_text)
        negative_sentiment = agent.analyze_sentiment(negative_text)

        assert positive_sentiment["sentiment"] == "positive"
        assert negative_sentiment["sentiment"] == "negative"

    def test_contact_info_extraction(self, agent):
        """Test contact information extraction"""
        text = "Contact us at john@example.com or call 555-123-4567"
        contact_info = agent.extract_contact_info(text)

        assert "john@example.com" in contact_info["emails"]
        assert "555-123-4567" in contact_info["phones"]

    @pytest.mark.asyncio
    async def test_agent_execution_no_urls(self, agent):
        """Test agent execution with no URLs"""
        input_data = AgentInput(
            request_id="test-123",
            input_data={"campaign_name": "Test without URLs"}
        )

        result = await agent.execute(input_data)

        assert "No URLs found" in result["message"]
        assert result["pages_crawled"] == 0

    @pytest.mark.asyncio
    async def test_agent_execution_with_mock_url(self, agent, sample_input):
        """Test agent execution with mocked URL fetching"""
        with patch.object(agent, 'fetch_page_content') as mock_fetch:
            # Mock successful page fetch
            mock_fetch.return_value = {
                "url": "https://example.com",
                "title": "Example Dental",
                "text_content": "We provide excellent dental services",
                "links": [],
                "images": [],
                "headings": {"h1": ["Welcome"], "h2": [], "h3": []},
                "meta_description": "Best dental services",
                "status_code": 200
            }

            result = await agent.execute(sample_input)

            assert result["pages_crawled"] == 1
            assert "example.com" in result["summary"]
            assert "structured_data" in result

    def test_invalid_url_detection(self, agent):
        """Test invalid URL detection"""
        valid_urls = ["https://example.com", "http://test.org"]
        invalid_urls = ["not-a-url", "ftp://invalid.com", ""]

        for url in valid_urls:
            assert agent.is_valid_url(url) == True

        for url in invalid_urls:
            assert agent.is_valid_url(url) == False

if __name__ == "__main__":
    # Run tests directly
    asyncio.run(pytest.main([__file__, "-v"]))
