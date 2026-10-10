#!/bin/bash
set -e

echo "========================================"
echo "  Furina MC Server - 阿里云 ECS 部署"
echo "========================================"

# 1. 更新系统 + 安装 Java 21
echo "[1/6] 安装 Java 21..."
apt update -qq && apt install -y -qq openjdk-21-jdk-headless
java -version

# 2. 创建目录
echo "[2/6] 创建服务器目录..."
mkdir -p /opt/minecraft/mods /opt/minecraft/config /opt/minecraft/world
cd /opt/minecraft

# 3. 下载 NeoForge 26.2 安装器
echo "[3/6] 下载 NeoForge..."
wget -q https://maven.neoforged.net/releases/net/neoforged/neoforge/26.2.0.43-beta/neoforge-26.2.0.43-beta-installer.jar -O neoforge-installer.jar

# 4. 安装 NeoForge 服务器
echo "[4/6] 安装 NeoForge 服务端..."
java -jar neoforge-installer.jar --installServer
rm neoforge-installer.jar

# 5. 创建启动脚本
echo "[5/6] 创建启动脚本..."
cat > start.sh << 'EOF'
#!/bin/bash
cd /opt/minecraft
java -Xms4G -Xmx6G @user_jvm_args.txt @libraries/net/neoforged/neoforge/26.2.0.43-beta/unix_args.txt nogui
EOF
chmod +x start.sh

# 6. 同意 EULA
echo "[6/6] 配置 EULA..."
echo "eula=true" > eula.txt

echo ""
echo "========================================"
echo "  ✅ 环境安装完成！"
echo "  现在需要上传 mods 和 world 文件"
echo "========================================"
