document.addEventListener('DOMContentLoaded', function() {
    // Initialize loading of dashboard data
    loadDashboardData();
});


async function loadDashboardData() {
    // Show loading indicator, hide content and error
    document.getElementById('dashboard-loading').classList.remove('hidden');
    document.getElementById('dashboard-content').classList.add('hidden');
    document.getElementById('dashboard-error').classList.add('hidden');
    try {
        if (!steamId)
        {
            throw new Error('No Steam ID available');
        }
        const [recentlyPlayedData, friendGamesData, recommendedGamesData] = await Promise.all([
            fetchRecentlyPlayedGames(steamId).catch(error => {
                console.error('Failed to fetch recently played games:', error);
                return { status: 'error', message: error.message, games: [] };
            }),
            fetchFriendGames(steamId).catch(error => {
                console.error('Failed to fetch friend games:', error);
                return { status: 'error', message: error.message, games: [] };
            }),
            fetchTrendingGames(steamId).catch(error => {
                console.error('Failed to fetch trending games:', error);
                return { status: 'error', message: error.message, games: [] };
            })
        ]);

        updateRecentlyPlayedSection(recentlyPlayedData);
        updateFriendsGamesSection(friendGamesData);
        updateRecommendedSection(recommendedGamesData);
        
        document.getElementById('dashboard-loading').classList.add('hidden');
        document.getElementById('dashboard-content').classList.remove('hidden');
        
    } catch (error) {
        console.error('Dashboard loading error:', error);
        
        const errorElement = document.getElementById('dashboard-error');
        errorElement.textContent = 'Error loading dashboard data: ' + error.message;
        errorElement.classList.remove('hidden');
        
        document.getElementById('dashboard-loading').classList.add('hidden');
    }
}


async function fetchRecentlyPlayedGames() {    
    try {
        const response = await fetch("/fetch-user-games?limit=6");
        
        if (!response.ok) throw new Error(`Server responded with status: ${response.status}`);
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching user games:', error);
        throw error;
    }
}

async function fetchFriendGames() {
    try {
        const response = await fetch("/fetch-friend-games?limit=6");
        
        if (!response.ok) throw new Error(`Server responded with status: ${response.status}`);
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching friend games:', error);
        throw error;
    }
}


async function fetchTrendingGames() {
    
    try {
        const response = await fetch("/fetch-recommendations?limit=6");
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching trending games:', error);
        throw error;
    }
}

function updateRecentlyPlayedSection(data) {
    const container = document.getElementById('recently-played-content');
    const counter = document.getElementById('recently-played-counter');
    const games = data.games_data;
    const games_info = data.games_info;
    const count = data.count;
    
    if (counter) counter.textContent = count;

    if (count === 0)
    {
        container.innerHTML = '<p>No recently played games found.</p>';
        return;
    }
    
    let html = '';
    games.forEach(game => {
        const app_id = game.app_id;
        const name = game.name;
        const imageUrl = game.images.capsule_image;
        const playtime = formatPlaytime(games_info[app_id].playtime);
        const lastPlayed = formatLastPlayed(games_info[app_id].last_played, games_info[app_id].playtime);
        
        html += `
        <div class="recommended-game">
            <img src="${imageUrl}" alt="${escapeHtml(name)}" class="game-img"">
            <div class="game-details">
                <h4>${escapeHtml(name)}</h4>
                <p>Last played: ${lastPlayed}</p>
                <p>Playtime: <span class="match-percentage">${playtime}</span></p>
            </div>
        </div>`;
    });
    
    container.innerHTML = html;

}

/**
 * Update the Games Friends Own section of the dashboard
 */
function updateFriendsGamesSection(data) {
    const container = document.getElementById('common-games-content');
    const counter = document.getElementById('common-games-counter');
    
    const games = data.games_data;
    const friends_games = data.friends_games;
    const count = data.count;
    
    if (counter) counter.textContent = count;
    
    if (count === 0)
    {
        container.innerHTML = '<p>No common games with friends found.</p>';
        return;
    }
    let html = '';
    Object.entries(friends_games).forEach(([appId, steamIds]) => {
        
        const name = games[appId].name;
        const imageUrl = games[appId].images.capsule_image;
        const user_games_info = data.user_games_info;
        
        // Get friend count information
        const friendCount = steamIds.length;
        const isOwned = appId in user_games_info;
        
        html += `
        <div class="recommended-game">
            <img src="${imageUrl}" alt="${escapeHtml(name)}" class="game-img"">
            <div class="game-details">
                <h4>
                    ${escapeHtml(name)}
                    ${isOwned ? '<span class="badge owned">Owned</span>' : ''}
                </h4>
                <p>${friendCount} friend${friendCount > 1 ? 's' : ''} play this game</p>
                <p>&nbsp;</p>
            </div>
        </div>`;
    });
    
    container.innerHTML = html;
}

/**
 * Update the Recommended For You section of the dashboard
 */
function updateRecommendedSection(data) {
    const container = document.getElementById('recommended-content');
    const counter = document.getElementById('recommended-counter');
    
    const games = data.games_data;
    const games_scores = data.scores;
    const count = data.count;
    
    if (counter) counter.textContent = count;
    
    if (count === 0)
    {
        container.innerHTML = '<p>No recommended games found.</p>';
        return;
    }
    
    let html = '';
    games_scores.forEach(([app_id, score]) => {
        
        const name = games[app_id].name;
        const imageUrl = games[app_id].images.capsule_image;
        // console.log(games[app_id].price);
        
        console.log(games[app_id].price)
        html += `
        <div class="recommended-game">
            <img src="${imageUrl}" alt="${escapeHtml(name)}" class="game-img" onerror="this.src='https://via.placeholder.com/120x45?text=No+Image'">
            <div class="game-details">
                <h4>${escapeHtml(name)}</h4>
                <p><span class="match-percentage">${score}% match</span> based on your preferences</p>
                <p>Price: ${formatPrice(games[app_id].price)}</p>
            </div>
        </div>`;
    });
    
    container.innerHTML = html;
}

function formatLastPlayed(timestamp, last_played) {
    if (!timestamp)
    {
        if(last_played) return 'Unavailable';
        return 'Never';
    }
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Today';
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        return `${weeks} week${weeks !== 1 ? 's' : ''} ago`;
    } else {
        return date.toLocaleDateString();
    }
}

/**
 * Format minutes into a readable playtime string
 */
function formatPlaytime(minutes) {
    if (!minutes) return 'No playtime';
    
    minutes = parseInt(minutes);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    
    if (hours > 0) {
        if (mins > 0) {
            return `${hours} hrs ${mins} mins`;
        }
        return `${hours} hrs`;
    }
    
    return `${mins} mins`;
}

function formatPrice(price)
{
    if (price.is_free) return 'Free';
    return price.final_price
    
}

/**
 * Format number with K/M suffix for large numbers
 */
function formatNumber(num) {
    if (!num) return '';
    
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    } else {
        return num.toString();
    }
}

function escapeHtml(text) {
    if (!text) return '';
    
    return text
        .toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}