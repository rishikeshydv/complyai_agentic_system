import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#101820",
        sand: "#f7f3eb",
        clay: "#c95f34",
        slate: "#30475e",
        mist: "#d2dae2",
      },
    },
  },
  plugins: [],
};

export default config;
