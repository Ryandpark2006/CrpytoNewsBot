import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import ccxt
from bs4 import BeautifulSoup
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Load environment variables
load_dotenv()

class CryptoNewsBot:
    def __init__(self):
        # Email credentials
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        
        # Initialize DeepSeek model
        print("Loading DeepSeek model... This might take a few minutes on first run...")
        self.tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-coder-6.7b-instruct", trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            "deepseek-ai/deepseek-coder-6.7b-instruct",
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        print("DeepSeek model loaded successfully!")
        
        # Initialize cryptocurrency exchange
        self.exchange = ccxt.binance()

    def get_crypto_news(self):
        """Fetch latest crypto news from various sources"""
        news = []
        
        # CoinDesk API
        try:
            response = requests.get('https://api.coindesk.com/v1/news/latest')
            if response.status_code == 200:
                articles = response.json()
                for article in articles[:3]:  # Get top 3 articles
                    news.append({
                        'source': 'CoinDesk',
                        'title': article['title'],
                        'url': article['url']
                    })
        except Exception as e:
            print(f"Error fetching CoinDesk news: {e}")

        return news

    def get_price_data(self):
        """Fetch price data for major cryptocurrencies"""
        try:
            symbols = ['BTC/USDT', 'ETH/USDT']
            price_data = {}
            
            for symbol in symbols:
                ticker = self.exchange.fetch_ticker(symbol)
                price_data[symbol] = {
                    'price': ticker['last'],
                    '24h_change': ticker['percentage']
                }
            
            return price_data
        except Exception as e:
            print(f"Error fetching price data: {e}")
            return {}

    def generate_article(self, news, price_data):
        """Generate an article-style summary using DeepSeek"""
        try:
            # Prepare the context
            context = "Here's the latest cryptocurrency market data and news:\n\n"
            
            # Add price information
            context += "Market Data:\n"
            for symbol, data in price_data.items():
                context += f"{symbol}: ${data['price']:,.2f} ({data['24h_change']:+.2f}%)\n"
            
            context += "\nRecent News:\n"
            for article in news:
                context += f"- {article['title']}\n"

            prompt = f"""Based on the following cryptocurrency market data and news, create a brief, engaging summary in a journalistic style. Focus on the most important trends and developments. Keep it concise and informative.

{context}

Write a summary that includes:
1. A catchy headline
2. Key market movements
3. Main news highlights
4. Brief analysis of the implications

Keep the tone professional but accessible.

Summary:"""

            # Generate response using DeepSeek
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                inputs["input_ids"],
                max_length=1000,
                temperature=0.7,
                do_sample=True,
                top_p=0.95,
                num_return_sequences=1,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            article = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Clean up the response to get only the generated part
            article = article.split("Summary:")[-1].strip()

            # Add source links at the bottom
            article += "\n\nSources:\n"
            for news_item in news:
                article += f"• {news_item['url']}\n"

            return article

        except Exception as e:
            print(f"Error generating article: {e}")
            return self.format_update(news, price_data)  # Fallback to basic format

    def format_update(self, news, price_data):
        """Format the crypto update for posting (fallback method)"""
        update = "🚀 Daily Crypto Update 🚀\n\n"
        
        # Add price information
        update += "📊 Market Update:\n"
        for symbol, data in price_data.items():
            update += f"{symbol}: ${data['price']:,.2f} ({data['24h_change']:+.2f}%)\n"
        
        update += "\n📰 Latest News:\n"
        for article in news:
            update += f"• {article['title']}\n{article['url']}\n"
        
        return update

    def send_email(self, update):
        """Send update via email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = self.email_address
            msg['Subject'] = f"Daily Crypto Market Update - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Create a more visually appealing HTML email
            update_html = update.replace("\n", "<br>")
            html_content = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                        .container {{ padding: 20px; }}
                        .header {{ color: #333; }}
                        .market-data {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                        .news {{ margin-top: 20px; }}
                        .source-links {{ margin-top: 20px; color: #666; }}
                        a {{ color: #007bff; text-decoration: none; }}
                        a:hover {{ text-decoration: underline; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        {update_html}
                    </div>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def run(self):
        """Run the bot"""
        news = self.get_crypto_news()
        price_data = self.get_price_data()
        
        # Generate article-style update
        update = self.generate_article(news, price_data)
        
        # Send email update
        if self.email_address and self.email_password:
            if self.send_email(update):
                print("Successfully sent email update")
            else:
                print("Failed to send email update")
        else:
            print("Email credentials not found. Please check your .env file.")

if __name__ == "__main__":
    bot = CryptoNewsBot()
    bot.run() 