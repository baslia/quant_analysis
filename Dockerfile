FROM python:3.10

# Install libraries
#RUN apt-get install -y libgtk-3-dev

# Update default packages
RUN apt-get update && apt-get -y install libgtk-3-0

# Get Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

COPY req_docker.txt ./requirements.txt

RUN pip3 install --no-cache-dir --upgrade pip

RUN pip3 install wheel

# Install pywry manually
RUN git clone https://github.com/OpenBB-finance/pywry.git
RUN cd pywry && pip install .[dev] && maturin build
#    pip install ./target/wheels/pywry-0.1.0-cp310-cp310-linux_x86_64.whl --force-reinstall

RUN pip3 install --no-cache-dir -r requirements.txt