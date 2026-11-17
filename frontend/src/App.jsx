import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function getWeatherInfo(code) {
  const types = {
    0: ["☀️", "Clear sky"],
    1: ["🌤️", "Mainly clear"],
    2: ["⛅", "Partly cloudy"],
    3: ["☁️", "Overcast"],
    45: ["🌫️", "Fog"],
    48: ["🌫️", "Fog"],
    51: ["🌦️", "Light drizzle"],
    53: ["🌦️", "Moderate drizzle"],
    55: ["🌧️", "Dense drizzle"],
    61: ["🌧️", "Slight rain"],
    63: ["🌧️", "Moderate rain"],
    65: ["🌧️", "Heavy rain"],
    71: ["🌨️", "Slight snow"],
    73: ["🌨️", "Moderate snow"],
    75: ["❄️", "Heavy snow"],
    80: ["🌦️", "Rain showers"],
    81: ["🌧️", "Moderate rain showers"],
    82: ["⛈️", "Heavy rain showers"],
    95: ["⛈️", "Thunderstorm"],
    96: ["⛈️", "Thunderstorm with hail"],
    99: ["⛈️", "Heavy thunderstorm"]
  };

  return types[code] || ["🌡️", "Unknown condition"];
}

function App() {
  const [city, setCity] = useState("");
  const [weather, setWeather] = useState(null);
  const [suggestions, setSuggestions] = useState([]);

  const [loading, setLoading] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [error, setError] = useState("");

  const [videos, setVideos] = useState([]);
  const [videosLoading, setVideosLoading] = useState(false);
  const [videosError, setVideosError] = useState("");

  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [dateWeather, setDateWeather] = useState(null);
  const [dateLoading, setDateLoading] = useState(false);
  const [dateError, setDateError] = useState("");

  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  const [records, setRecords] = useState([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState("");

  const [editingId, setEditingId] = useState(null);
  const [editStartDate, setEditStartDate] = useState("");
  const [editEndDate, setEditEndDate] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  useEffect(() => {
    loadRecords();
  }, []);

  // Load YouTube weather videos
  async function loadWeatherVideos(location) {
    setVideosLoading(true);
    setVideosError("");
    setVideos([]);

    try {
      const response = await fetch(
        `${API_URL}/api/videos?location=${encodeURIComponent(location)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load weather videos.");
      }

      setVideos(data.videos || []);
    } catch (err) {
      setVideosError(err.message);
    } finally {
      setVideosLoading(false);
    }
  }

  // Search location suggestions
  async function findLocations(value) {
    setCity(value);
    setSuggestions([]);

    if (value.trim().length < 2) return;

    try {
      const response = await fetch(
        `${API_URL}/api/location?location=${encodeURIComponent(value)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Location search failed.");
      }

      setSuggestions(data.locations || []);
    } catch (err) {
      console.error(err);
    }
  }

  // Search weather by city
  async function searchWeather(selectedCity = city) {
    if (!selectedCity.trim()) {
      setError("Please enter a city name.");
      return;
    }

    setLoading(true);
    setError("");
    setSuggestions([]);
    setWeather(null);
    setVideos([]);
    setVideosError("");
    setDateWeather(null);
    setDateError("");
    setSaveMessage("");

    try {
      const response = await fetch(
        `${API_URL}/api/weather?location=${encodeURIComponent(selectedCity)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to retrieve weather.");
      }

      setWeather(data);
      setCity(selectedCity);

      loadWeatherVideos(data.location.name || selectedCity);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Get weather using GPS
  function useMyLocation() {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }

    setGpsLoading(true);
    setError("");
    setWeather(null);
    setVideos([]);
    setVideosError("");
    setDateWeather(null);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;

        try {
          const response = await fetch(
            `${API_URL}/api/weather/coordinates?latitude=${latitude}&longitude=${longitude}`
          );

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.detail || "Unable to get local weather.");
          }

          setWeather(data);
          setCity(data.location.name);
          setSuggestions([]);

          loadWeatherVideos(data.location.name);
        } catch (err) {
          setError(err.message);
        } finally {
          setGpsLoading(false);
        }
      },
      () => {
        setError("Unable to access your location. Please allow location access.");
        setGpsLoading(false);
      }
    );
  }

  // Search weather by date range
  async function searchDateWeather() {
    if (!weather) {
      setDateError("Search for a city or use your location first.");
      return;
    }

    if (!startDate || !endDate) {
      setDateError("Please select both dates.");
      return;
    }

    if (startDate > endDate) {
      setDateError("Start date must be before end date.");
      return;
    }

    setDateLoading(true);
    setDateError("");
    setDateWeather(null);
    setSaveMessage("");

    try {
      const latitude = weather.location.latitude;
      const longitude = weather.location.longitude;

      const response = await fetch(
        `${API_URL}/api/weather/date-range?latitude=${latitude}&longitude=${longitude}&start_date=${startDate}&end_date=${endDate}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to retrieve weather.");
      }

      setDateWeather(data);
    } catch (err) {
      setDateError(err.message);
    } finally {
      setDateLoading(false);
    }
  }

  // Save weather search
  async function saveWeatherRecord() {
    if (!weather || !dateWeather) {
      setDateError("Search for weather dates first.");
      return;
    }

    setSaving(true);
    setDateError("");
    setSaveMessage("");

    try {
      const response = await fetch(`${API_URL}/api/records`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          location: weather.location.name,
          country: weather.location.country || "",
          latitude: weather.location.latitude,
          longitude: weather.location.longitude,
          start_date: startDate,
          end_date: endDate,
          humidity: currentWeather?.relative_humidity_2m ?? null,
          wind_speed: currentWeather?.wind_speed_10m ?? null
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to save record.");
      }

      setSaveMessage("Weather search saved successfully!");
      await loadRecords();
    } catch (err) {
      setDateError(err.message);
    } finally {
      setSaving(false);
    }
  }

  // Load saved records
  async function loadRecords() {
    setRecordsLoading(true);
    setRecordsError("");

    try {
      const response = await fetch(`${API_URL}/api/records`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load records.");
      }

      setRecords(data);
    } catch (err) {
      setRecordsError(err.message);
    } finally {
      setRecordsLoading(false);
    }
  }

  function startEditing(record) {
    setEditingId(record.id);
    setEditStartDate(record.start_date);
    setEditEndDate(record.end_date);
  }

  function cancelEditing() {
    setEditingId(null);
    setEditStartDate("");
    setEditEndDate("");
  }

  // Update a saved record
  async function updateRecord(recordId) {
    if (!editStartDate || !editEndDate) {
      setRecordsError("Please select both dates.");
      return;
    }

    if (editStartDate > editEndDate) {
      setRecordsError("Start date must be before end date.");
      return;
    }

    setEditLoading(true);
    setRecordsError("");

    try {
      const response = await fetch(
        `${API_URL}/api/records/${recordId}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            start_date: editStartDate,
            end_date: editEndDate
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to update record.");
      }

      cancelEditing();
      await loadRecords();
    } catch (err) {
      setRecordsError(err.message);
    } finally {
      setEditLoading(false);
    }
  }

  // Delete a saved record
  async function deleteRecord(recordId) {
    const confirmed = window.confirm(
      "Are you sure you want to delete this weather record?"
    );

    if (!confirmed) return;

    setRecordsError("");

    try {
      const response = await fetch(
        `${API_URL}/api/records/${recordId}`,
        { method: "DELETE" }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to delete record.");
      }

      await loadRecords();
    } catch (err) {
      setRecordsError(err.message);
    }
  }

  // Download CSV, JSON, XML, PDF or Markdown
  async function downloadExport(format) {
    try {
      const response = await fetch(
        `${API_URL}/api/export/${format}`
      );

      if (!response.ok) {
        throw new Error("Unable to download export.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = `weather_records.${format}`;

      document.body.appendChild(link);
      link.click();

      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setRecordsError(err.message);
    }
  }

  const currentWeather = weather?.weather?.current;
  const dailyWeather = weather?.weather?.daily;

  return (
    <div className="app-container">

      {/* Header */}
      <header className="app-header">
        <h1>WeatherWise</h1>
        <p>Your everyday weather companion</p>
      </header>

      <main className="main-content">

        {/* City Search */}
        <section className="search-section">
          <h2>Check the Weather</h2>
          <p>Discover weather conditions for any city.</p>

          <div className="search-box">
            <input
              type="text"
              value={city}
              onChange={(e) => findLocations(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") searchWeather();
              }}
              placeholder="Enter city name..."
            />

            <button onClick={() => searchWeather()}>
              Search
            </button>
          </div>

          {suggestions.length > 0 && (
            <div className="suggestions-list">
              {suggestions.map((item, index) => (
                <button
                  key={`${item.latitude}-${item.longitude}-${index}`}
                  className="suggestion-item"
                  onClick={() => searchWeather(item.name)}
                >
                  {item.name}
                  {item.admin1 ? `, ${item.admin1}` : ""}
                  {item.country ? `, ${item.country}` : ""}
                </button>
              ))}
            </div>
          )}

          <button
            className="location-button"
            onClick={useMyLocation}
            disabled={gpsLoading}
          >
            {gpsLoading ? "Getting Location..." : "📍 Use My Location"}
          </button>

          {loading && <p>Loading weather...</p>}
          {error && <p className="error-message">{error}</p>}
        </section>

        {/* Weather Information */}
        {weather && (
          <section className="weather-section">

            <h2>
              {weather.location.name}
              {weather.location.admin1
                ? `, ${weather.location.admin1}`
                : ""}
              {weather.location.country
                ? `, ${weather.location.country}`
                : ""}
            </h2>

            {currentWeather && (
              <>
                <div className="weather-condition">
                  <span className="weather-icon">
                    {getWeatherInfo(currentWeather.weather_code)[0]}
                  </span>

                  <h3>
                    {getWeatherInfo(currentWeather.weather_code)[1]}
                  </h3>
                </div>

                <div className="weather-details">
                  <div className="weather-card">
                    <h4>Temperature</h4>
                    <p>{currentWeather.temperature_2m}°C</p>
                  </div>

                  <div className="weather-card">
                    <h4>Feels Like</h4>
                    <p>{currentWeather.apparent_temperature}°C</p>
                  </div>

                  <div className="weather-card">
                    <h4>Humidity</h4>
                    <p>{currentWeather.relative_humidity_2m}%</p>
                  </div>

                  <div className="weather-card">
                    <h4>Wind Speed</h4>
                    <p>{currentWeather.wind_speed_10m} km/h</p>
                  </div>
                </div>
              </>
            )}

            {/* Five-Day Forecast */}
            {dailyWeather && (
              <div className="forecast-section">
                <h2>5-Day Forecast</h2>

                <div className="forecast-container">
                  {dailyWeather.time?.map((day, index) => {
                    const [icon, description] = getWeatherInfo(
                      dailyWeather.weather_code[index]
                    );

                    return (
                      <div className="forecast-card" key={day}>
                        <h4>
                          {new Date(`${day}T00:00:00`).toLocaleDateString(
                            "en-US",
                            { weekday: "short" }
                          )}
                        </h4>

                        <p>{day}</p>
                        <span className="forecast-icon">{icon}</span>

                        <p className="forecast-description">
                          {description}
                        </p>

                        <p>
                          {dailyWeather.temperature_2m_max[index]}°C /
                          {" "}
                          {dailyWeather.temperature_2m_min[index]}°C
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Google Maps */}
            <div className="map-link">
              <a
                href={weather.map_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                View location on Google Maps
              </a>
            </div>

            {/* YouTube Weather Videos */}
            <section className="youtube-section">
              <h2>Weather Videos</h2>
              <p>
                Watch weather updates and forecasts for {weather.location.name}.
              </p>

              {videosLoading && <p>Loading weather videos...</p>}

              {videosError && (
                <p className="error-message">{videosError}</p>
              )}

              {!videosLoading && !videosError && videos.length === 0 && (
                <p>No weather videos found for this location.</p>
              )}

              {!videosLoading && videos.length > 0 && (
                <div className="youtube-grid">
                  {videos.map((video) => (
                    <a
                      className="youtube-card"
                      key={video.video_id}
                      href={video.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <img
                        src={video.thumbnail}
                        alt={video.title}
                        className="youtube-thumbnail"
                      />

                      <div className="youtube-info">
                        <h3>{video.title}</h3>
                        <p>{video.channel}</p>
                        <span>▶ Watch on YouTube</span>
                      </div>
                    </a>
                  ))}
                </div>
              )}
            </section>

            {/* Date Range Weather */}
            <section className="date-range-section">
              <h2>Weather by Date Range</h2>
              <p>Explore historical or upcoming weather conditions.</p>

              <div className="date-inputs">
                <div>
                  <label htmlFor="start-date">Start Date</label>
                  <input
                    id="start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>

                <div>
                  <label htmlFor="end-date">End Date</label>
                  <input
                    id="end-date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <button
                className="date-search-button"
                onClick={searchDateWeather}
                disabled={dateLoading}
              >
                {dateLoading ? "Searching..." : "Search Date Range"}
              </button>

              {dateError && (
                <p className="error-message">{dateError}</p>
              )}

              {dateWeather?.daily?.time && (
                <>
                  <div className="date-results">
                    <h3>Weather Results</h3>

                    {dateWeather.daily.time.map((day, index) => {
                      const [icon, description] = getWeatherInfo(
                        dateWeather.daily.weather_code[index]
                      );

                      return (
                        <div className="date-result-card" key={day}>
                          <h4>{day}</h4>
                          <span className="forecast-icon">{icon}</span>
                          <p>{description}</p>

                          <p>
                            Maximum:{" "}
                            {dateWeather.daily.temperature_2m_max[index]}°C
                          </p>

                          <p>
                            Minimum:{" "}
                            {dateWeather.daily.temperature_2m_min[index]}°C
                          </p>

                          <p>
                            Rainfall:{" "}
                            {dateWeather.daily.precipitation_sum?.[index] ?? "N/A"} mm
                          </p>
                        </div>
                      );
                    })}
                  </div>

                  <button
                    className="date-search-button"
                    onClick={saveWeatherRecord}
                    disabled={saving}
                  >
                    {saving ? "Saving..." : "💾 Save Weather Search"}
                  </button>

                  {saveMessage && (
                    <p className="success-message">{saveMessage}</p>
                  )}
                </>
              )}
            </section>
          </section>
        )}

        {/* Saved Weather Records */}
        <section className="saved-records-section">
          <h2>Saved Weather Records</h2>
          <p>Manage your previously saved weather searches.</p>

          <div className="export-buttons">
            <button onClick={() => downloadExport("csv")}>
              Download CSV
            </button>

            <button onClick={() => downloadExport("json")}>
              Download JSON
            </button>

            <button onClick={() => downloadExport("xml")}>
              Download XML
            </button>

            <button onClick={() => downloadExport("pdf")}>
              Download PDF
            </button>

            <button onClick={() => downloadExport("markdown")}>
              Download Markdown
            </button>

            <button onClick={loadRecords} disabled={recordsLoading}>
              {recordsLoading ? "Refreshing..." : "Refresh Records"}
            </button>
          </div>

          {recordsError && (
            <p className="error-message">{recordsError}</p>
          )}

          {recordsLoading && <p>Loading saved records...</p>}

          {!recordsLoading && records.length === 0 && (
            <p>No saved weather records yet.</p>
          )}

          {records.map((record) => (
            <div className="saved-record-card" key={record.id}>
              <h3>
                {record.location}, {record.country}
              </h3>

              <p>Record ID: {record.id}</p>

              {editingId === record.id ? (
                <div className="edit-record-form">
                  <label>Start Date</label>
                  <input
                    type="date"
                    value={editStartDate}
                    onChange={(e) => setEditStartDate(e.target.value)}
                  />

                  <label>End Date</label>
                  <input
                    type="date"
                    value={editEndDate}
                    onChange={(e) => setEditEndDate(e.target.value)}
                  />

                  <div className="record-actions">
                    <button
                      onClick={() => updateRecord(record.id)}
                      disabled={editLoading}
                    >
                      {editLoading ? "Updating..." : "Save Changes"}
                    </button>

                    <button onClick={cancelEditing}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p>
                    <strong>Start Date:</strong> {record.start_date}
                  </p>

                  <p>
                    <strong>End Date:</strong> {record.end_date}
                  </p>

                  <p>
                    <strong>Average Temperature:</strong>{" "}
                    {record.temperature ?? "N/A"}°C
                  </p>

                  <p>
                    <strong>Weather:</strong>{" "}
                    {record.weather_description || "N/A"}
                  </p>

                  <p>
                    <strong>Humidity:</strong>{" "}
                    {record.humidity ?? "N/A"}%
                  </p>

                  <p>
                    <strong>Wind Speed:</strong>{" "}
                    {record.wind_speed ?? "N/A"} km/h
                  </p>

                  <div className="record-actions">
                    <button onClick={() => startEditing(record)}>
                      Edit
                    </button>

                    <button
                      className="delete-button"
                      onClick={() => deleteRecord(record.id)}
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </section>

        {/* About WeatherWise */}
        <section className="about-section">
          <h2>About WeatherWise</h2>

          <p>
            WeatherWise is a full-stack weather application developed by
            Nasrin Shafikha as part of the PM Accelerator AI Engineer
            Intern Technical Assessment.
          </p>

          <h3>About PM Accelerator</h3>

          <p>
            PM Accelerator supports aspiring and experienced product
            managers through practical training, mentorship, and
            career development opportunities.
          </p>

          <p>
            <strong>Developed by:</strong> Nasrin Shafikha
          </p>

          <p>
            <strong>Technology:</strong> React, FastAPI, Python, SQLite,
            Open-Meteo API and YouTube Data API.
          </p>
        </section>

      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>
          WeatherWise | Built for the PM Accelerator AI Engineer Intern Assessment
        </p>
      </footer>

    </div>
  );
}

export default App;
