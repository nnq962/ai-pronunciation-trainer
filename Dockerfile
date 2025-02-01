# Sử dụng CUDA 12.6 cho Ubuntu 22.04 làm base image
FROM nvidia/cuda:12.6.3-base-ubuntu22.04

# Cài đặt các dependencies hệ thống cần thiết (ví dụ: Python và các thư viện hệ thống)
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    curl \
    ffmpeg \
    && apt-get clean

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Copy file yêu cầu vào container
COPY requirements_linux.txt .

# Cài đặt các dependencies Python
RUN pip3 install --no-cache-dir -r requirements_linux.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Mở cổng 3000 cho Flask (cổng mặc định của ứng dụng Flask)
EXPOSE 3000

# Khởi chạy ứng dụng Flask
CMD ["python3", "api.py"]
