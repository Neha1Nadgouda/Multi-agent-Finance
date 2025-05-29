from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()

class LanguageAgent:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo",
            request_timeout=10,
            api_key=self.openai_api_key
        )
        self.memory = ConversationBufferMemory()
        
        self.prompt = PromptTemplate(
            input_variables=["input"],
            template="""
            System: You are a professional financial analyst providing market briefings.
            Your responses should be clear, concise, and focused on the most important information.
            Use natural, conversational language while maintaining professionalism.
            When discussing numbers, round to 2 decimal places and include relevant units.

            {input}

            Please provide a market brief based on the above information.
            Focus on the key points and any significant changes or risks.
            """
        )
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.memory,
            verbose=True
        )

    def _format_input(self, query: str, analysis: Dict[str, Any], market_data: Dict[str, Any]) -> str:
        """Format the input data for the prompt"""
        try:
            # Format market data
            market_summary = []
            if isinstance(market_data, dict):
                if "stocks" in market_data:
                    stocks = market_data["stocks"]
                    for symbol, data in stocks.items():
                        if isinstance(data, dict):
                            market_summary.append(
                                f"- {symbol}: Price ${data.get('price', 0):.2f}, "
                                f"Change {data.get('change', 0):.2f}%, "
                                f"Volume {data.get('volume', 0):,}"
                            )
            
            # Format analysis data
            analysis_points = []
            if isinstance(analysis, dict):
                if "market_summary" in analysis:
                    summary = analysis["market_summary"]
                    analysis_points.extend([
                        f"Market Cap: ${summary.get('total_market_cap', 0):,.2f}",
                        f"Average Change: {summary.get('average_change', 0):.2f}%",
                        f"Volatility: {summary.get('volatility', 0):.2f}%"
                    ])
                
                if "risk_clusters" in analysis:
                    for cluster in analysis["risk_clusters"]:
                        if isinstance(cluster, dict):
                            analysis_points.append(
                                f"Risk Level {cluster.get('risk_level', 'Unknown')}: "
                                f"{', '.join(cluster.get('symbols', []))}"
                            )
            
            # Combine all information
            formatted_input = f"""
            Query: {query}

            Market Data:
            {chr(10).join(market_summary) if market_summary else "No market data available"}

            Analysis:
            {chr(10).join(analysis_points) if analysis_points else "No analysis available"}
            """
            
            return formatted_input
            
        except Exception as e:
            print(f"Error formatting input: {str(e)}")
            return f"""
            Query: {query}
            Market Data: Error formatting market data
            Analysis: Error formatting analysis data
            """

    async def generate_response(
        self,
        query: str,
        analysis: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> str:
        """Generate natural language response"""
        try:
            # Format the input data
            formatted_input = self._format_input(query, analysis, market_data)
            
            # Generate response
            response = await self.chain.arun(input=formatted_input)
            return response.strip()
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble analyzing the market data at the moment. Please try again or rephrase your query."

    async def health_check(self) -> Dict[str, Any]:
        """Check if the language model is working"""
        try:
            test_response = await self.generate_response(
                query="Test query",
                analysis={"status": "test"},
                market_data={"test": "data"}
            )
            return {
                "healthy": True,
                "timestamp": datetime.now().isoformat(),
                "last_response": test_response is not None
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
