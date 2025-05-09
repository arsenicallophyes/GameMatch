// js/profile.js
// steamGames is passed from the PHP file

const gamesContainer = document.getElementById('games-container');

if (steamGames.games && steamGames.games.length > 0) 
{
    steamGames.games.sort((a, b) => b.playtime_forever - a.playtime_forever);
    
    steamGames.games.forEach(game =>
        {
            const gameCard = document.createElement('div');
            gameCard.className = 'game-card';
            
            const imgUrl = `http://media.steampowered.com/steamcommunity/public/images/apps/${game.appid}/${game.img_icon_url}.jpg`;
            const playtimeHours = Math.round(game.playtime_forever / 60 * 10) / 10;
            
            gameCard.innerHTML = `
                <img src="${imgUrl}" alt="${game.name}" onerror="this.src='placeholder.png'">
                <div class="game-info">
                    <div class="game-title">${game.name}</div>
                    <div class="game-playtime">${playtimeHours} hours played</div>
                </div>
            `;
            
            gamesContainer.appendChild(gameCard);
        }
    );
}
else
{
    gamesContainer.innerHTML = '<p>No games found in your library</p>';
}
