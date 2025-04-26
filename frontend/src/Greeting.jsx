// src/Greeting.jsx
import React from 'react'; // Still needed for JSX

function Greeting(props) {
  // The component returns JSX defining its UI
  return <h1>Hello {props.name}! Welcome!</h1>;
}

export default Greeting; // Make the component available for use in other files