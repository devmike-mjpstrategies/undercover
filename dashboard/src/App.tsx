import { useEffect, useState } from "react";
import { Queue } from "./Queue";
import { parseRoute, type Route } from "./route";

function View({ route }: Readonly<{ route: Route }>) {
  switch (route.page) {
    case "claim":
    case "instructions":
    case "queue":
      return <Queue />;
  }
}

export function App() {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));

  useEffect(() => {
    const onChange = () => {
      setRoute(parseRoute(window.location.hash));
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => {
      window.removeEventListener("hashchange", onChange);
    };
  }, []);

  return (
    <>
      <header className="header">
        <span className="brand">UnderCover</span>
        <span className="tagline">Travel insurance claims</span>
        <nav className="nav" aria-label="Main">
          <a
            href="#/"
            aria-current={route.page === "queue" ? "page" : undefined}
          >
            Queue
          </a>
        </nav>
      </header>
      <main className="page">
        <View route={route} />
      </main>
    </>
  );
}
