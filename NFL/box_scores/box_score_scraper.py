"""
NFL Box Score Scraper - Enhanced Version with Team Stats
Scrapes detailed game results and team statistics from ESPN's API, organized by week
GitHub Actions Compatible Version
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from datetime import datetime


class NFLEnhancedBoxScoreScraper:
    def __init__(self, season, output_dir):
        """
        Initialize the scraper
        
        Args:
            season (int): NFL season year (e.g., 2025)
            output_dir (str): Directory to save CSV files
        """
        self.season = season
        self.output_dir = output_dir
        self.base_url = "https://site.api.espn.com"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"NFL Enhanced Box Score Scraper initialized for {season} season")
        print(f"Output directory: {output_dir}\n")
    
    def get_game_ids_for_week(self, week):
        """
        Get all game IDs for a specific week
        
        Args:
            week (int): Week number
            
        Returns:
            list: List of game IDs
        """
        url = f"{self.base_url}/apis/site/v2/sports/football/nfl/scoreboard?week={week}&seasontype=2&dates={self.season}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            time.sleep(2)
            
            data = response.json()
            game_ids = []
            
            if 'events' in data:
                for event in data['events']:
                    game_ids.append(event['id'])
            
            return game_ids
            
        except Exception as e:
            print(f"Error getting game IDs for week {week}: {e}")
            return []
    
    def get_game_details(self, game_id, week):
        """
        Get detailed statistics for a single game
        
        Args:
            game_id (str): ESPN game ID
            week (int): Week number
            
        Returns:
            dict: Dictionary with comprehensive game data
        """
        url = f"{self.base_url}/apis/site/v2/sports/football/nfl/summary?event={game_id}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            time.sleep(2)  # Be respectful to the server
            
            data = response.json()
            
            # Initialize game data
            game_data = {
                'week': week,
                'season': self.season,
                'game_id': game_id
            }
            
            # Get basic game info
            if 'header' in data and 'competitions' in data['header']:
                competition = data['header']['competitions'][0]
                
                # Get date
                game_data['date'] = competition.get('date', '')
                
                # Get teams and scores
                competitors = competition.get('competitors', [])
                if len(competitors) >= 2:
                    away_team = competitors[1] if competitors[1]['homeAway'] == 'away' else competitors[0]
                    home_team = competitors[0] if competitors[0]['homeAway'] == 'home' else competitors[1]
                    
                    game_data['away_team'] = away_team['team']['displayName']
                    game_data['away_team_abbr'] = away_team['team']['abbreviation']
                    game_data['away_score'] = int(away_team['score'])
                    
                    game_data['home_team'] = home_team['team']['displayName']
                    game_data['home_team_abbr'] = home_team['team']['abbreviation']
                    game_data['home_score'] = int(home_team['score'])
                    
                    # Winner
                    if game_data['away_score'] > game_data['home_score']:
                        game_data['winner'] = game_data['away_team']
                    elif game_data['home_score'] > game_data['away_score']:
                        game_data['winner'] = game_data['home_team']
                    else:
                        game_data['winner'] = 'TIE'
                    
                    game_data['point_differential'] = abs(game_data['away_score'] - game_data['home_score'])
                
                # Get status
                game_data['status'] = competition.get('status', {}).get('type', {}).get('description', '')
            
            # Get team statistics from boxscore
            if 'boxscore' in data and 'teams' in data['boxscore']:
                teams = data['boxscore']['teams']
                
                for team_data in teams:
                    team_name = team_data['team']['displayName']
                    prefix = 'away_' if team_name == game_data.get('away_team') else 'home_'
                    
                    # Extract statistics
                    if 'statistics' in team_data:
                        for stat in team_data['statistics']:
                            stat_name = stat.get('name', '')
                            stat_value = stat.get('displayValue', '')
                            
                            # Handle special formats that need to be split
                            if stat_name == 'totalPenaltiesYards':
                                # Split "7-64" into penalties (7) and penalty yards (64)
                                if '-' in stat_value:
                                    parts = stat_value.split('-')
                                    game_data[f"{prefix}penalties"] = parts[0]
                                    game_data[f"{prefix}penaltyYards"] = parts[1]
                                else:
                                    game_data[f"{prefix}penalties"] = stat_value
                                    game_data[f"{prefix}penaltyYards"] = ''
                            
                            elif stat_name == 'completionAttempts':
                                # Split "26/41" into completions (26) and attempts (41)
                                if '/' in stat_value:
                                    parts = stat_value.split('/')
                                    game_data[f"{prefix}completions"] = parts[0]
                                    game_data[f"{prefix}passAttempts"] = parts[1]
                                else:
                                    game_data[f"{prefix}completions"] = stat_value
                                    game_data[f"{prefix}passAttempts"] = ''
                            
                            elif stat_name == 'thirdDownEff':
                                # Split "7-14" into third down conversions (7) and attempts (14)
                                if '-' in stat_value:
                                    parts = stat_value.split('-')
                                    game_data[f"{prefix}thirdDownConversions"] = parts[0]
                                    game_data[f"{prefix}thirdDownAttempts"] = parts[1]
                                else:
                                    game_data[f"{prefix}thirdDownConversions"] = stat_value
                                    game_data[f"{prefix}thirdDownAttempts"] = ''
                            
                            elif stat_name == 'fourthDownEff':
                                # Split "1-2" into fourth down conversions (1) and attempts (2)
                                if '-' in stat_value:
                                    parts = stat_value.split('-')
                                    game_data[f"{prefix}fourthDownConversions"] = parts[0]
                                    game_data[f"{prefix}fourthDownAttempts"] = parts[1]
                                else:
                                    game_data[f"{prefix}fourthDownConversions"] = stat_value
                                    game_data[f"{prefix}fourthDownAttempts"] = ''
                            
                            elif stat_name == 'sacksYardsLost':
                                # Split "2-10" into sacks (2) and sack yards lost (10)
                                if '-' in stat_value:
                                    parts = stat_value.split('-')
                                    game_data[f"{prefix}sacks"] = parts[0]
                                    game_data[f"{prefix}sackYardsLost"] = parts[1]
                                else:
                                    game_data[f"{prefix}sacks"] = stat_value
                                    game_data[f"{prefix}sackYardsLost"] = ''
                            
                            else:
                                # For all other stats, keep as-is
                                column_name = f"{prefix}{stat_name}"
                                game_data[column_name] = stat_value
            
            # Get additional game details
            if 'gameInfo' in data:
                game_info = data['gameInfo']
                game_data['attendance'] = game_info.get('attendance', '')
                
                if 'venue' in game_info:
                    game_data['venue'] = game_info['venue'].get('fullName', '')
                    game_data['venue_city'] = game_info['venue'].get('address', {}).get('city', '')
                    game_data['venue_state'] = game_info['venue'].get('address', {}).get('state', '')
            
            return game_data
            
        except Exception as e:
            print(f"  Error getting details for game {game_id}: {e}")
            return None
    
    def scrape_week_with_stats(self, week):
        """
        Scrape all games for a week with detailed statistics
        
        Args:
            week (int): Week number
            
        Returns:
            pd.DataFrame: DataFrame with comprehensive game data
        """
        print(f"Scraping Week {week} with detailed stats...")
        
        # Get all game IDs for the week
        game_ids = self.get_game_ids_for_week(week)
        
        if not game_ids:
            print(f"  No games found for Week {week}")
            return pd.DataFrame()
        
        print(f"  Found {len(game_ids)} games")
        
        # Get detailed data for each game
        games_data = []
        for i, game_id in enumerate(game_ids, 1):
            print(f"  Fetching game {i}/{len(game_ids)} (ID: {game_id})...")
            game_data = self.get_game_details(game_id, week)
            if game_data:
                games_data.append(game_data)
        
        if games_data:
            df = pd.DataFrame(games_data)
            print(f"  Successfully scraped {len(games_data)} games\n")
            return df
        else:
            print(f"  No data collected for Week {week}\n")
            return pd.DataFrame()
    
    def save_week_data(self, df, week):
        """
        Save week data to CSV
        
        Args:
            df (pd.DataFrame): DataFrame with week data
            week (int): Week number
        """
        if df.empty:
            print(f"  No data to save for Week {week}")
            return
        
        filename = os.path.join(self.output_dir, f'week_{week}.csv')
        df.to_csv(filename, index=False)
        print(f"Saved: {filename} ({len(df)} games, {len(df.columns)} columns)\n")
    
    def scrape_all_weeks(self, start_week=1, end_week=18):
        """
        Scrape all weeks in the specified range
        
        Args:
            start_week (int): First week to scrape
            end_week (int): Last week to scrape
        """
        print(f"Starting enhanced scrape for {self.season} NFL season")
        print(f"Weeks {start_week} to {end_week}")
        print(f"=" * 60 + "\n")
        
        for week in range(start_week, end_week + 1):
            df = self.scrape_week_with_stats(week)
            
            if not df.empty:
                self.save_week_data(df, week)
            else:
                print(f"Skipping Week {week} - no data available\n")
        
        print("=" * 60)
        print(f"Scraping complete! Data saved to: {self.output_dir}")
        print("\nYour CSV files now include:")
        print("  - Basic game info (teams, scores, date, venue)")
        print("  - Team statistics (for both teams)")
        print("  - Attendance and venue details")


if __name__ == "__main__":
    # Configuration
    SEASON = 2025  # Current season
    
    # Get output directory from environment variable or use default
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR', 'NFL/box_scores/2025')
    
    # Get week range from environment variables or use defaults
    START_WEEK = int(os.environ.get('START_WEEK', 1))
    END_WEEK = int(os.environ.get('END_WEEK', 22))
    
    print("=" * 60)
    print("NFL ENHANCED BOX SCORE SCRAPER")
    print("=" * 60)
    print("\nThis version includes detailed team statistics!")
    print("Stats include: passing yards, rushing yards, turnovers,")
    print("time of possession, and much more.\n")
    
    # Create scraper and run
    scraper = NFLEnhancedBoxScoreScraper(SEASON, OUTPUT_DIR)
    scraper.scrape_all_weeks(START_WEEK, END_WEEK)
    
    print("\n" + "=" * 60)
    print("DONE! Data saved to repository.")
    print("=" * 60)
