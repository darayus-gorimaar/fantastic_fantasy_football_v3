import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [leagueId, setLeagueId] = useState("");
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [trades, setTrades] = useState([]);
  const [positionsOfStrength, setPositionsOfStrength] = useState([]);
  const [positionsOfNeed, setPositionsOfNeed] = useState([]);

  const updateLeagueId = async () => {
    try {
      const response = await fetch("/setLeagueId", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ leagueId }),
      });
      if (response.ok) {
        // Do nothing
      } else {
        console.error("Failed to update League ID");
      }
    } catch (error) {
      console.error("Error:", error);
    } finally {
      // Set loading state to false after the request completes
    }
  };

  const getUsers = async () => {
    console.log("Getting users...");
    try {
      const response = await fetch(`/getLeagueUsers/${leagueId}`);
      if (response.ok) {
        const u = await response.json();
        console.log(u);
        setUsers(u.users);
      } else {
        console.error("Failed to fetch users");
      }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const getTrades = async (username) => {
    setTrades([]);
    try {
      const response = await fetch(
        `/getTradeOpportunitiesFromOwner/${leagueId}/${username}`
      );
      if (response.ok) {
        const t = await response.json();
        console.log(t);
        setTrades(t);
      } else {
        console.error("Failed to fetch trades");
      }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const getPositionsOfNeed = async (username) => {
    setPositionsOfNeed([]);
    try {
      const response = await fetch(
        `/getOwnerPositionsOfNeed/${leagueId}/${username}`
      );
      if (response.ok) {
        const n = await response.json();
        console.log(n.positions_of_need);
        setPositionsOfNeed(n.positions_of_need);
      } else {
        console.error("Failed to fetch owner positions of need");
      }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const getPositionsOfStrength = async (username) => {
    setPositionsOfStrength([]);
    try {
      const response = await fetch(
        `/getOwnerPositionsOfStrength/${leagueId}/${username}`
      );
      if (response.ok) {
        const s = await response.json();
        console.log(s.positions_of_strength);
        setPositionsOfStrength(s.positions_of_strength);
        // console.log("Pos of strength stored:", positionsOfStrength);
      } else {
        console.error("Failed to fetch owner positions of strength");
      }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  useEffect(() => {
    if (selectedUser) {
      getPositionsOfNeed(selectedUser.display_name);
      getPositionsOfStrength(selectedUser.display_name);
      getTrades(selectedUser.display_name);
    }
  }, [selectedUser]);

  return (
    <div>
      <main className="container">
        <div>Sample Sleeper League ID: 1181833854536986624</div>
        <div className="card">
          <h2 className="card-title">Enter Your League</h2>
          <p className="card-description">
            Start by entering your fantasy league ID
          </p>
          <div className="input-group">
            <input
              type="text"
              className="input"
              placeholder="Enter league ID"
              value={leagueId}
              onChange={(e) => setLeagueId(e.target.value)}
            />
            <button
              className="button button-primary"
              onClick={() => {
                updateLeagueId();
                getUsers();
              }}
            >
              Load League
            </button>
          </div>
        </div>

        {users.length > 0 && (
          <div className="card">
            <h2 className="card-title">Select Your Team</h2>
            <p className="card-description">
              Choose your team to see trade recommendations
            </p>
            <div className="user-grid">
              {users.map((user, index) => (
                <button
                  key={index}
                  className={`user-button ${
                    selectedUser === user ? "active" : ""
                  }`}
                  onClick={() => setSelectedUser(user)}
                >
                  <img
                    src={`https://sleepercdn.com/avatars/thumbs/${user.avatar}`}
                    alt={user.display_name}
                    className="user-avatar"
                  />
                  <span>{user.display_name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {selectedUser && (
          <div className="main-content">
            <div className="card">
              <h2 className="card-title">Team Analysis</h2>
              <p className="card-description">
                {selectedUser.display_name}'s team strengths and needs
              </p>
              <div>
                <h3>Positions of Strength</h3>
                <div>
                  {positionsOfStrength.length === 0 ? (
                    <div>Loading...</div>
                  ) : (
                    positionsOfStrength.map((pos, idx) => (
                      <span key={idx} className="badge badge-strength">
                        {pos}
                      </span>
                    ))
                  )}
                </div>
              </div>
              <div>
                <h3>Positions of Need</h3>
                <div>
                  {positionsOfNeed.length === 0 ? (
                    <div>Loading...</div>
                  ) : (
                    positionsOfNeed.map((pos, idx) => (
                      <span key={idx} className="badge badge-need">
                        {pos}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="card">
              <h2 className="card-title">Recommended Trades</h2>
              <p className="card-description">
                Trade proposals to improve your team
              </p>

              {trades.length === 0 ? (
                <div>Loading...</div>
              ) : (
                trades.map((trade, index) => (
                  <div key={index} className="trade-proposal">
                    <div className="player-card">
                      <div className="player-info">
                        <span className="player-name">{trade.add_player}</span>
                        <span className="player-rating">
                          Rating: {trade.add_rating}
                        </span>
                        <span className="player-position">
                          Position: {trade.add_position}
                        </span>
                      </div>
                    </div>
                    <span className="trade-icon">
                      <img
                        src="https://img.icons8.com/flat-round/50/sorting-arrows-horizontal.png"
                        alt="for"
                      />
                    </span>
                    <div className="player-card player-card-right">
                      <div className="player-info">
                        <span className="player-name">{trade.send_player}</span>
                        <span className="player-rating">
                          Rating: {trade.send_rating}
                        </span>
                        <span className="player-position">
                          Position: {trade.send_position}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
