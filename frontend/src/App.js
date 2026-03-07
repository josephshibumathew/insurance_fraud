import React from "react";

import AppRoutes from "./routes";
import ErrorBoundary from "./components/common/ErrorBoundary";

function App() {
	return (
		<ErrorBoundary>
			<AppRoutes />
		</ErrorBoundary>
	);
}

export default App;

