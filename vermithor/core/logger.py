import logging
import os


def setup_logger():

    os.makedirs(
        "data",
        exist_ok=True
    )

    logging.basicConfig(
        filename="data/vermithor.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    return logging.getLogger("Vermithor")