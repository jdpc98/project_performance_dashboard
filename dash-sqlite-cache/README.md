# Dash SQLite Cache Application

This project is a Dash web application that utilizes a local SQLite database for caching data. The application is designed to efficiently load and manage data while providing a responsive user interface.

## Project Structure

```
dash-sqlite-cache
├── src
│   ├── app.py                # Main Dash application
│   ├── data_manager.py       # Data loading and cache management
│   ├── components
│   │   ├── __init__.py
│   │   ├── layout.py         # App layout components
│   │   └── callbacks.py      # Callback definitions
│   ├── utils
│   │   ├── __init__.py
│   │   └── helpers.py        # Helper functions
│   └── database
│       ├── __init__.py
│       ├── models.py         # SQLite table definitions
│       └── cache.py          # Cache operations
├── data
│   └── cache.db              # SQLite database file
├── static
│   └── styles.css            # Custom CSS styles
├── tests
│   ├── __init__.py
│   ├── test_data_manager.py
│   └── test_cache.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd dash-sqlite-cache
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python src/app.py
   ```

2. Open your web browser and navigate to `http://127.0.0.1:8050` to view the application.

## Features

- **Data Caching**: Utilizes SQLite for caching data to improve performance and reduce loading times.
- **Responsive UI**: Built with Dash, providing an interactive user experience.
- **Modular Structure**: Organized into components for easy maintenance and scalability.

## Testing

To run the tests, use the following command:
```
pytest
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.