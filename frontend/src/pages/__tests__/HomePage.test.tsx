import { render, screen } from '@testing-library/react';
import HomePage from '../HomePage';

describe('HomePage', () => {
  it('renders home page', () => {
    render(<HomePage />);
    expect(screen.getByText('GambleGlee')).toBeInTheDocument();
  });

  it('shows welcome message', () => {
    render(<HomePage />);
    expect(screen.getByText(/Welcome to GambleGlee/)).toBeInTheDocument();
  });
});
