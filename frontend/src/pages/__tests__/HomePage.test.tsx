import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import HomePage from "../HomePage";

describe("HomePage", () => {
  it("renders home page", () => {
    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );
    // Check for the main heading instead of just "GambleGlee" to avoid multiple matches
    expect(screen.getByText("Social Betting Made")).toBeInTheDocument();
  });

  it("shows welcome message", () => {
    render(
      <BrowserRouter>
        <HomePage />
      </BrowserRouter>
    );
    // Check for actual text that exists in the component
    expect(screen.getByText(/Challenge your friends, make predictions/)).toBeInTheDocument();
  });
});
