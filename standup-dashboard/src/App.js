import React, { useState, useEffect } from "react";
import {
	Calendar,
	Users,
	MessageSquare,
	TrendingUp,
	AlertCircle,
	CheckCircle,
	Clock,
	RefreshCw,
	Database,
	Cpu,
} from "lucide-react";
import "./App.css";

const StandupDashboard = () => {
	const [selectedDate, setSelectedDate] = useState(
		new Date().toISOString().split("T")[0],
	);
	const [channels, setChannels] = useState([]);
	const [loading, setLoading] = useState(true);
	const [lastUpdated, setLastUpdated] = useState(new Date());
	const [useMockData, setUseMockData] = useState(true);
	const [error, setError] = useState(null);
	const [summaryLoading, setSummaryLoading] = useState({});

	// Mock data generator
	const generateMockData = () => {
		const channelNames = [
			"Frontend Team",
			"Backend Team",
			"DevOps Team",
			"QA Team",
			"Mobile Team",
			"Design Team",
			"Product Team",
			"Data Team",
			"Security Team",
			"Infrastructure Team",
		];

		const mockSummaries = [
			"Team made significant progress on user authentication module. Sarah completed the login flow redesign, while Mike fixed 3 critical bugs in the API endpoints. Planning to deploy to staging tomorrow. No major blockers reported.",
			"Sprint goals are on track. Database optimization reduced query times by 40%. John is working on payment integration, expected completion by Friday. Minor concern with third-party service reliability.",
			"Infrastructure updates completed successfully. CI/CD pipeline improvements reduced deployment time by 30%. Monitoring new auto-scaling policies. One team member mentioned potential capacity issues next week.",
			"Testing coverage improved to 85%. Found 2 regression bugs in the checkout flow, already assigned to developers. Automation suite running smoothly. Team morale is high with good collaboration.",
			"iOS app store review submitted. Android build has performance improvements. React Native upgrade caused minor styling issues, fix in progress. Release candidate ready for internal testing.",
			"User research findings presented to stakeholders. New wireframes for dashboard redesign completed. Usability testing scheduled for next week. Team excited about upcoming feature launches.",
			"Roadmap priorities finalized for Q4. Customer feedback analysis revealed 3 key improvement areas. Working closely with engineering on technical feasibility. Stakeholder alignment looks good.",
			"ML model accuracy improved by 12%. Data pipeline optimization reduced processing time. Working on feature engineering for recommendation system. Need more computational resources for training.",
			"Security audit findings addressed. Vulnerability scanning completed with no critical issues. Team completed security training modules. Preparing for compliance review next month.",
			"Network latency improvements deployed. Server capacity planning for holiday traffic completed. Backup systems tested successfully. Monitoring alerting system upgrades in progress.",
		];

		const statuses = ["healthy", "warning", "critical"];
		const messageCounts = [12, 8, 15, 6, 20, 9, 11, 14, 7, 18];
		const memberCounts = [5, 4, 6, 3, 8, 4, 5, 7, 3, 6];

		return channelNames.map((name, index) => ({
			id: `channel-${index}`,
			channel_id: `C${index}`,
			channel_name: name,
			summary: mockSummaries[index],
			message_count: messageCounts[index],
			memberCount: memberCounts[index],
			status: statuses[index % 3],
			lastActivity: new Date(
				Date.now() - Math.random() * 3600000,
			).toLocaleTimeString("en-US", {
				hour: "2-digit",
				minute: "2-digit",
			}),
		}));
	};

	// Fetch real data from API
	const fetchRealData = async () => {
		try {
			const response = await fetch(
				`${process.env.REACT_APP_API_BASE_URL || "http://localhost:3001"}/api/channels?date=${selectedDate}`,
			);
			if (!response.ok) {
				throw new Error("Failed to fetch channels");
			}
			const channelsData = await response.json();

			// Generate summaries for each channel
			const channelsWithSummaries = await Promise.all(
				channelsData.map(async (channel) => {
					const summary = await generateSummary(
						channel.channel_id,
						channel.channel_name,
					);
					return {
						...channel,
						id: channel.channel_id,
						summary: summary,
						memberCount: Math.floor(Math.random() * 8) + 3, // Mock member count
						status:
							channel.message_count > 10
								? "healthy"
								: channel.message_count > 5
									? "warning"
									: "critical",
						lastActivity: new Date(
							Date.now() - Math.random() * 3600000,
						).toLocaleTimeString("en-US", {
							hour: "2-digit",
							minute: "2-digit",
						}),
					};
				}),
			);

			return channelsWithSummaries;
		} catch (err) {
			console.error("Error fetching real data:", err);
			setError(err.message);
			return [];
		}
	};

	// Generate AI summary for a channel
	const generateSummary = async (channelId, channelName) => {
		setSummaryLoading((prev) => ({ ...prev, [channelId]: true }));

		try {
			// Get messages for the channel
			const messagesResponse = await fetch(
				`${process.env.REACT_APP_API_BASE_URL || "http://localhost:3001"}/api/messages/${channelId}?date=${selectedDate}`,
			);
			if (!messagesResponse.ok) {
				throw new Error("Failed to fetch messages");
			}
			const messages = await messagesResponse.json();

			if (messages.length === 0) {
				return "No messages found for this date.";
			}

			// Generate summary
			const summaryResponse = await fetch(
				`${process.env.REACT_APP_API_BASE_URL || "http://localhost:3001"}/api/summary`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
					},
					body: JSON.stringify({
						messages,
						date: selectedDate,
						channelName,
					}),
				},
			);

			if (!summaryResponse.ok) {
				// Try to get the error message from the response
				const errorData = await summaryResponse.json();
				throw new Error(errorData.error || "Failed to generate summary");
			}

			const summaryData = await summaryResponse.json();
			return summaryData.summary;
		} catch (err) {
			console.error("Error generating summary:", err);
			// Return a more user-friendly error message
			return `Unable to generate summary. Please check your API configuration and try again.`;
		} finally {
			setSummaryLoading((prev) => ({ ...prev, [channelId]: false }));
		}
	};
	// Load data based on toggle
	const loadData = async () => {
		setLoading(true);
		setError(null);

		try {
			if (useMockData) {
				// Simulate API delay
				await new Promise((resolve) => setTimeout(resolve, 1000));
				setChannels(generateMockData());
			} else {
				const realData = await fetchRealData();
				setChannels(realData);
			}
		} catch (err) {
			setError(err.message);
		} finally {
			setLoading(false);
			setLastUpdated(new Date());
		}
	};

	useEffect(() => {
		loadData();
	}, [selectedDate, useMockData]);

	const getStatusColor = (status) => {
		switch (status) {
			case "healthy":
				return "bg-green-100 text-green-800 border-green-200";
			case "warning":
				return "bg-yellow-100 text-yellow-800 border-yellow-200";
			case "critical":
				return "bg-red-100 text-red-800 border-red-200";
			default:
				return "bg-gray-100 text-gray-800 border-gray-200";
		}
	};

	const getStatusIcon = (status) => {
		switch (status) {
			case "healthy":
				return <CheckCircle className="w-4 h-4" />;
			case "warning":
				return <AlertCircle className="w-4 h-4" />;
			case "critical":
				return <AlertCircle className="w-4 h-4" />;
			default:
				return <Clock className="w-4 h-4" />;
		}
	};

	return (
		<div className="dashboard-container">
			<div className="dashboard-wrapper">
				{/* Header */}
				<div className="dashboard-header">
					<div className="header-row">
						<h1 className="dashboard-title">Standup Dashboard</h1>
						<div className="header-controls">
							{/* Data Source Toggle */}
							<div className="data-source-toggle">
								<span className="toggle-label">Data Source:</span>
								<button
									onClick={() => setUseMockData(!useMockData)}
									className={`toggle-button ${useMockData ? "mock" : "real"}`}
								>
									{useMockData ? (
										<Cpu className="w-4 h-4" />
									) : (
										<Database className="w-4 h-4" />
									)}
									{useMockData ? "Mock Data" : "Real Data"}
								</button>
							</div>

							{/* Refresh Button */}
							<button
								onClick={loadData}
								className="refresh-button"
								disabled={loading}
							>
								<RefreshCw className={`w-4 h-4 ${loading ? "spin" : ""}`} />
								Refresh
							</button>
						</div>
					</div>

					<div className="controls-row">
						<div className="date-picker-wrapper">
							<Calendar className="w-5 h-5" />
							<input
								type="date"
								value={selectedDate}
								onChange={(e) => setSelectedDate(e.target.value)}
								className="date-picker"
							/>
						</div>
						<div className="last-updated">
							Last updated: {lastUpdated.toLocaleTimeString()}
						</div>
						{error && <div className="error-message">Error: {error}</div>}
					</div>
				</div>

				{/* Stats Overview */}
				<div className="stats-grid">
					<div className="stat-card">
						<div className="stat-content">
							<div className="stat-icon blue">
								<Users />
							</div>
							<div className="stat-info">
								<p className="stat-label">Total Channels</p>
								<p className="stat-value">{channels.length}</p>
							</div>
						</div>
					</div>

					<div className="stat-card">
						<div className="stat-content">
							<div className="stat-icon green">
								<CheckCircle />
							</div>
							<div className="stat-info">
								<p className="stat-label">Healthy Teams</p>
								<p className="stat-value">
									{channels.filter((c) => c.status === "healthy").length}
								</p>
							</div>
						</div>
					</div>

					<div className="stat-card">
						<div className="stat-content">
							<div className="stat-icon yellow">
								<AlertCircle />
							</div>
							<div className="stat-info">
								<p className="stat-label">Need Attention</p>
								<p className="stat-value">
									{channels.filter((c) => c.status === "warning").length}
								</p>
							</div>
						</div>
					</div>

					<div className="stat-card">
						<div className="stat-content">
							<div className="stat-icon purple">
								<MessageSquare />
							</div>
							<div className="stat-info">
								<p className="stat-label">Total Messages</p>
								<p className="stat-value">
									{channels.reduce((sum, c) => sum + c.message_count, 0)}
								</p>
							</div>
						</div>
					</div>
				</div>

				{/* Channel Grid */}
				{loading ? (
					<div className="loading-grid">
						{Array.from({ length: 6 }).map((_, index) => (
							<div key={index} className="loading-card">
								<div className="loading-bar title"></div>
								<div className="loading-bar"></div>
								<div className="loading-bar small"></div>
								<div className="loading-bar large"></div>
							</div>
						))}
					</div>
				) : (
					<div className="channels-grid">
						{channels.map((channel) => (
							<div key={channel.id} className="channel-card">
								{/* Header */}
								<div className="channel-header">
									<div className="channel-info">
										<h3>{channel.channel_name}</h3>
										<div className="channel-stats">
											<div className="channel-stat">
												<Users />
												{channel.memberCount} members
											</div>
											<div className="channel-stat">
												<MessageSquare />
												{channel.message_count} messages
											</div>
										</div>
									</div>
									<div className={`status-badge ${channel.status}`}>
										{getStatusIcon(channel.status)}
										{channel.status}
									</div>
								</div>

								{/* Summary */}
								<div className="summary-section">
									<h4 className="summary-title">AI Summary</h4>
									{summaryLoading[channel.channel_id] ? (
										<div className="summary-loading">
											<RefreshCw className="spin" />
											Generating summary...
										</div>
									) : (
										<p className="summary-content">{channel.summary}</p>
									)}
								</div>

								{/* Footer */}
								<div className="channel-footer">
									<span>Last activity: {channel.lastActivity}</span>
									<span className="footer-activity">
										<TrendingUp />
										Active
									</span>
								</div>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	);
};

export default StandupDashboard;
