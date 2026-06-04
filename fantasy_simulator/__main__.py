"""Allow ``python -m fantasy_simulator`` to launch the orchestrator."""

from fantasy_simulator.simulation_engine import main

if __name__ == "__main__":
    raise SystemExit(main())
