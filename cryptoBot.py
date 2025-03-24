import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import ccxt
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

class CryptoNewsBot:
    def __init__(self):
        # Email credentials
        self.email_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        
        # Initialize cryptocurrency exchange
        self.exchange = ccxt.binance()

    def get_crypto_news(self):
        """Fetch latest crypto news from CryptoPanic API"""
        news = []
        try:
            response = requests.get("https://cryptopanic.com/api/v1/posts/?auth_token=25fa36640e61ce6bbabb3bd0c45f1ac0c67a5a62&filter=trending")
            if response.status_code == 200:
                articles = response.json().get("results", [])
                for article in articles[:3]:  # Get top 3 articles
                    news.append({
                        'source': article['domain'],
                        'title': article['title'],
                        'url': article['url']
                    })
        except Exception as e:
            print(f"Error fetching news: {e}")

        return news


    def get_price_data(self):
        """Fetch price data for major cryptocurrencies using CoinGecko."""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin,ethereum",
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            response = requests.get(url, params=params)
            data = response.json()

            price_data = {
                "BTC/USDT": {
                    "price": data["bitcoin"]["usd"],
                    "24h_change": data["bitcoin"].get("usd_24h_change", 0)
                },
                "ETH/USDT": {
                    "price": data["ethereum"]["usd"],
                    "24h_change": data["ethereum"].get("usd_24h_change", 0)
                }
            }

            return price_data
        except Exception as e:
            print(f"Error fetching price data: {e}")
            return {}


    def format_update(self, news, price_data):
        """Format the crypto update"""
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
            
            msg.attach(MIMEText(update, 'plain'))
            
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
        
        # Format update
        update = self.format_update(news, price_data)
        
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
