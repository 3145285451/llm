from ninja import NinjaAPI, Router, File
from django.http import HttpRequest, StreamingHttpResponse
from ninja.files import UploadedFile as NinjaUploadedFile
from typing import Optional, Generator
from . import services
from django.conf import settings
from .schemas import LoginIn, LoginOut, ChatIn, ChatOut, HistoryOut, ErrorResponse
from .models import APIKey
from .services import get_or_create_session, model_api_call
from datetime import datetime
import logging
import re
import time
import json

logger = logging.getLogger(__name__)

api = NinjaAPI(title="DeepSeek-R1:7B API", version="0.0.1")


# 硬编码的术语词典，可根据需要扩展
# -*- coding: utf-8 -*-

# 这是一个整合了所有领域技术术语的词汇表字典
# 用于大模型故障分析诊断项目的前端悬停解释功能

GLOSSARY_ENTRIES = {
    # === LLM 及通用术语 ===
    "LLM": "大型语言模型（Large Language Model），指通过海量数据训练以理解和生成自然语言的模型。",
    "SSE": "Server-Sent Events，一种基于 HTTP 的单向服务器推送技术，常用于流式返回数据。",
    "向量检索": "利用向量化表示进行相似度搜索的技术，常用于语义匹配和知识库检索。",
    "RAG": "Retrieval-Augmented Generation，一种结合了检索（Retrieval）和生成（Generation）的范式，通过从外部知识库检索信息来增强大型语言模型（LLM）的回答质量和准确性。",
    "上下文窗口 (Context Window)": "在大模型推理时可同时处理的最大 token 数量，超出后需要截断或滑动窗口处理。",
    "Token": "文本被模型处理的最小单位，可以是一个词、一个字或一个子词。",
    "Prompt": "(提示词) 输入给大模型的指令或问题，用于引导模型生成期望的输出。",
    "推理 (Inference)": "模型训练完成后，使用模型根据新输入（Prompt）生成结果的过程。",
    "微调 (Fine-tuning)": "在一个已经预训练好的大模型基础上，使用特定领域或任务的数据集进行额外训练，以使模型更适应特定需求。",
    "量化 (Quantization)": "一种模型压缩技术，通过降低模型参数的数值精度（例如从32位浮点数降至8位整数）来减少模型大小和计算量，以提升推理速度。",
    "KV Cache": "(键值缓存) 在模型（尤其是Transformer架构）生成文本时，用于缓存先前计算过的键（Key）和值（Value）向量的技术。它能显著加快后续Token的生成速度，是流式输出（如SSE）的基础。",
    "SFT": "(Supervised Fine-Tuning) 监督微调，使用“指令-回答”对的数据集来训练模型，使其学会遵循指令和进行对话。",
    # === Linux 错误与术语 ===
    "dmesg": "(Diagnostic Message) 一种命令，用于显示内核环形缓冲区（kernel ring buffer）的消息。当系统启动失败、硬件故障或驱动程序出问题时，这是首选的排错工具。",
    "Kernel Panic": "(内核恐慌) Linux 内核遇到无法恢复的致命错误时的一种状态。系统会停止所有处理，并通常会显示一条错误消息。",
    "OOM Killer": "(Out of Memory Killer) 当系统物理内存和交换空间（Swap）均耗尽时，内核会激活 OOM Killer。它会根据一套评分机制（oom_score）选择并终止一个或多个进程，以释放内存，保护系统免于崩溃。",
    "Segmentation Fault (SIGSEGV)": "(段错误) 进程试图访问其无权访问的内存地址（例如，访问空指针、越界访问数组）时发生的错误。",
    "Zombie Process": "(僵尸进程) 已完成执行（已退出）但其父进程尚未读取其退出状态的进程。僵尸进程本身不占用CPU，但会占用进程表中的一个条目。",
    "inode": "(索引节点) 在类 Unix 文件系统中，用于存储文件元数据（如权限、所有者、大小、时间戳以及数据块位置）的数据结构。",
    "EACCES (Permission denied)": "(权限被拒绝) 错误码13。进程试图以其权限（用户、组、其他）不允许的方式访问文件或资源。",
    "ENOENT (No such file or directory)": "(无此文件或目录) 错误码2。当程序试图访问一个不存在的文件路径时返回。",
    "EPERM (Operation not permitted)": "(操作不被允许) 错误码1。通常发生在进程试图执行一个需要更高权限（如 root 权限）的操作时。",
    "fsck": "(File System Check) 用于检查和修复类 Unix 文件系统一致性错误的工具。",
    "Systemd": "Linux 系统的初始化系统（init system）和服务管理器，负责在启动时引导系统并管理系统服务（daemons）。",
    "journalctl": "用于查询和显示 systemd 日志（journal）的命令。",
    "Load Average": "(系统平均负载) 对系统在特定时间段内（通常是1分钟、5分钟、15分钟）的CPU队列长度（正在运行或等待CPU的进程数）的度量。",
    # === 路由器错误与术语 ===
    "BGP": "(Border Gateway Protocol) 边界网关协议。用于在互联网上的自治系统（AS）之间交换路由和可达性信息的路由协议。",
    "OSPF": "(Open Shortest Path First) 开放最短路径优先。一种内部网关协议（IGP），使用链路状态算法在单个自治系统（AS）内部计算路由。",
    "ACL": "(Access Control List) 访问控制列表。一组规则，用于定义允许或拒绝哪些数据包通过网络接口。",
    "NAT": "(Network Address Translation) 网络地址转换。一种将IP数据包头中的私有IP地址和端口号转换为公网IP地址和端口号（反之亦然）的技术。",
    "Packet Drop": "(丢包) 数据包在网络传输过程中（如在路由器上）因各种原因（如拥塞、ACL拒绝、TTL超时、CRC错误）而被丢弃。",
    "CRC Error": "(Cyclic Redundancy Check Error) 循环冗余校验错误。表明在物理层传输过程中数据帧已损坏。通常指向有问题的电缆、端口或网卡。",
    "Interface Flapping": "(接口抖动) 网络接口（端口）在“up”（启用）和“down”（禁用）状态之间快速、反复地切换。这通常表示物理层或数据链路层存在问题。",
    "Latency": "(延迟) 数据包从源头发送到目的地所需的时间，通常以来回时间（RTT）衡量。",
    "Jitter": "(抖动) 延迟的变化。高抖动对实时应用（如VoIP、视频会议）尤其有害。",
    "MTU Mismatch": "(Maximum Transmission Unit Mismatch) 最大传输单元不匹配。当网络路径上相邻的两个设备配置了不同的 MTU 大小，可能导致数据包被分片或丢弃，引发性能问题。",
    "TTL Expired (Time to Live Expired)": "(生存时间到期) IP数据包中的TTL字段每经过一个路由器就会减1。当TTL减到0时，数据包被丢弃，并向源发送ICMP“Time Exceeded”消息。这通常用于防止路由循环。",
    # === Windows 错误与术语 ===
    "BSOD": "(Blue Screen of Death) 蓝屏死机。Windows 遇到严重的系统错误（如驱动程序冲突、硬件故障）时显示的停止错误屏幕。",
    "Event ID": "(事件ID) Windows 事件查看器 (Event Viewer) 中用于唯一标识特定系统事件（信息、警告、错误）的编号。",
    "Event Viewer": "(事件查看器) 一个 Windows 内置工具，用于查看和管理系统日志，包括应用程序日志、安全日志和系统日志。",
    "0x80070005": "(E_ACCESSDENIED) 一个常见的 Windows 错误代码，表示“访问被拒绝”。通常与文件权限、注册表权限或 DCOM 权限有关。",
    "0x000000F4": "(CRITICAL_OBJECT_TERMINATION) 一个常见的 BSOD 停止代码，表示一个关键的系统进程或线程意外终止。",
    "Registry": "(注册表) Windows 系统中用于存储系统配置、硬件设置、软件首选项和用户配置的层次化数据库。",
    "svchost.exe": "(Service Host) Windows 中的一个通用宿主进程，用于运行一个或多个 Windows 服务（DLL形式）。",
    "WMI": "(Windows Management Instrumentation) Windows 管理规范。微软实现的一种技术，允许脚本和管理应用程序在本地或远程管理 Windows 系统。",
    "HKEY_LOCAL_MACHINE (HKLM)": "注册表中的一个根键（Root Key），包含特定于本地计算机的配置信息（如硬件和软件设置）。",
    "NTFS": "(New Technology File System) Windows NT 系列操作系统的标准文件系统。",
    "Access Denied": "(访问被拒绝) 见 0x80070005。当用户或进程试图访问其没有权限的文件、文件夹、注册表项或其他对象时发生。",
    "DLL": "(Dynamic Link Library) 动态链接库。包含可被多个程序同时使用的代码和数据的文件。",
    # === LevelDB 错误与术语 ===
    "SSTable": "(Sorted String Table) LevelDB 中用于在磁盘上持久化存储键值对的文件格式。SSTable 中的键是排序的且文件本身是不可变的。",
    "MemTable": "(Memory Table) 内存中的数据结构（通常是跳表 Skip List），用于缓存最近的写入操作。当 MemTable 达到一定大小时，它会被冻结并刷新（flush）到磁盘，成为一个新的 SSTable。",
    "Compaction": "(压缩/合并) LevelDB 的后台过程，用于合并不同层级（Level）的 SSTable 文件。它能移除已删除或已覆盖的键，并减少读取时需要检查的文件数量。",
    "Corruption": "(数据损坏) 错误状态，表示数据库文件（SSTable、Manifest 或日志）的内容与预期不符或已损坏。",
    "IOError": "(I/O 错误) LevelDB 在尝试读取或写入磁盘文件时遇到的操作系统级别错误（如磁盘已满、文件不可读）。",
    "NotFound": "(未找到) 这是一个状态而非严格意义上的错误，表示尝试读取的键（Key）在数据库中不存在。",
    "Log file (.log)": "(日志文件) LevelDB 在将数据写入 MemTable 之前，会先将操作写入日志文件（也称为 WAL，Write-Ahead Log）。这确保了即使系统崩溃，重启时也能通过重放日志来恢复 MemTable 中的数据。",
    "Manifest": "(清单文件) 存储数据库元数据的文件，如数据库处于哪个版本、每个层级有哪些 SSTable 文件、它们的键范围等。",
    "Write-Ahead Log (WAL)": "(预写日志) 见 Log file。一种确保数据持久性的标准技术。",
    "Level-0": "(L0层) MemTable 被刷新后生成的 SSTable 所在的层级。L0 层比较特殊，它允许 SSTable 之间的键范围重叠。",
    # === MySQL 错误与术语 ===
    "ER_ACCESS_DENIED_ERROR": "(1045) 拒绝访问错误。通常是因为用户名、密码或客户端主机地址不正确，导致连接被拒绝。",
    "ER_NO_SUCH_TABLE": "(1146) 无此表错误。查询试图访问一个在当前数据库中不存在的表。",
    "Deadlock": "(死锁) 两个或多个事务（Transaction）相互持有对方需要的锁，并都在等待对方释放，导致所有事务都无法继续执行。InnoDB 会自动检测死锁并回滚其中一个事务。",
    "Row Lock": "(行锁) 数据库锁定（Locking）的一种粒度，仅锁定正在被修改的行，允许其他事务访问同一张表中的不同行。InnoDB 存储引擎使用行锁。",
    "InnoDB": "MySQL 默认的事务型存储引擎。支持事务（ACID）、行级锁定和外键。",
    "Slow Query Log": "(慢查询日志) MySQL 的一种日志，用于记录执行时间超过 `long_query_time` 设定阈值的 SQL 查询。",
    "Replication Lag": "(复制延迟) 在 MySQL 主从复制（Replication）中，从库（Slave/Replica）应用主库（Master/Source）的 binlog 事件所需的时间与主库生成该事件的时间之间的差值。",
    "binlog": "(Binary Log) 二进制日志。记录所有修改了数据库数据的操作（DML）以及数据定义（DDL）。主要用于数据恢复和主从复制。",
    "GTID": "(Global Transaction Identifier) 全局事务标识符。在 MySQL 复制中，为每个已提交的事务分配的唯一ID。它简化了主从切换和故障恢复。",
    "max_connections": "(最大连接数) MySQL 服务器允许的并发客户端连接的最大数量。连接数超限（Too many connections）是常见的错误。",
    "Wait_timeout": "服务器关闭非交互式连接（如连接池连接）之前等待其活动的秒数。超时后连接被断开，可能导致“MySQL server has gone away”错误。",
    "MyISAM": "MySQL 早期的存储引擎，不支持事务和行锁，但读取性能较高。现在已不推荐使用。",
    # === Redis 错误与术语 ===
    "OOM command not allowed": "(内存溢出命令不允许) 当 Redis 占用的内存达到了 `maxmemory` 配置的上限，并且 `maxmemory-policy` 设置为 `noeviction` 时，任何会导致内存增加的写入命令（如 SET, PUSH）都会返回此错误。",
    "MISCONF": "(配置错误) 通常与 Redis Sentinel 或持久化（Persistence）相关。例如，当 RDB 或 AOF 持久化失败时，Redis 可能会配置为停止接受写入，此时会返回此错误。",
    "maxmemory": "Redis 的配置参数，用于限制实例可以使用的最大内存量。",
    "AOF": "(Append Only File) 追加式文件持久化。Redis 将所有收到的写入命令以日志形式追加到文件中。恢复时，Redis 只需重新执行 AOF 文件中的所有命令。",
    "RDB": "(Redis Database) 快照持久化。Redis 在特定时间点将其内存中的数据集合生成一个二进制快照文件（.rdb）。",
    "Replication": "(复制) Redis 的主从复制机制，允许从节点（Replica）拥有主节点（Master）数据的完整副本。",
    "Sentinel": "(哨兵) Redis の高可用性解决方案。Sentinel 系统会监控 Redis 主从实例，并在主节点下线时自动执行故障转移（Failover），将一个从节点提升为新的主节点。",
    "Cluster": "(集群) Redis 的分布式解决方案，用于将数据分片（Sharding）存储在多个 Redis 节点上，以实现水平扩展。",
    "Connection refused": "(连接被拒绝) 客户端尝试连接 Redis 端口，但被操作系统拒绝。常见原因包括 Redis 服务未启动、防火墙拦截或 `bind` 配置错误（例如 Redis 只监听了 127.0.0.1，而客户端从外部访问）。",
    "MOVED": "(重定向 - 集群) 在 Redis Cluster 中，当客户端请求的键（Key）所在的哈希槽（Slot）不由当前节点负责时，节点会返回一个 `MOVED` 错误，告诉客户端该槽位由哪个节点（IP和端口）负责。",
    "ASK": "(重定向 - 迁移中) 在 Redis Cluster 中，当一个哈希槽正在从一个节点迁移到另一个节点时，如果客户端请求的键可能在目标节点上，源节点会返回 `ASK` 重定向。",
    "Persistence": "(持久化) 指 Redis 将内存中的数据写入磁盘的过程，以防止在服务器重启或崩溃时丢失数据。主要方式是 RDB 和 AOF。",
    # === Apache 错误与术语 ===
    "httpd": "(HTTP Daemon) Apache HTTP 服务器的后台守护进程（服务）的名称。",
    ".htaccess": "Apache 的按目录配置的配置文件。它允许在特定目录及其子目录中覆盖服务器的主配置（例如，设置 `mod_rewrite` 规则）。",
    "mod_rewrite": "Apache 的一个强大模块，用于基于正则表达式重写（Rewrite）请求的 URL。",
    "403 Forbidden": "(HTTP 403 禁止) 服务器理解了请求，但拒绝授权执行。这通常由文件系统权限（例如 httpd 进程无权读取文件）或 Apache 配置（例如 `Require all denied`）引起。",
    "500 Internal Server Error": "(HTTP 500 内部服务器错误) 一个通用的服务器错误状态码，表示服务器在执行请求时遇到了意外情况。在 Apache 中，这通常由 `.htaccess` 文件中的语法错误、CGI 脚本失败或配置错误引起。",
    "AH00558": "(Could not reliably determine the server's fully qualified domain name) Apache 启动时常见的警告信息。意味着 Apache 无法解析在 `ServerName` 指令中设置的主机名。虽然通常无害，但建议修复。",
    "MaxClients": "(在 Apache 2.4+ 中称为 MaxRequestWorkers) Apache（使用 MPM prefork 模式时）可以启动的用于处理请求的子进程的最大数量。达到此限制后，新的连接将排队等待。",
    "KeepAlive": "HTTP 持久连接功能。如果启用，允许客户端在同一个 TCP 连接上发送多个 HTTP 请求，减少了建立和拆除 TCP 连接的开销。",
    "Access Log": "(访问日志) 记录所有发送到服务器的 HTTP 请求的日志文件（例如，`access_log`）。",
    "Error Log": "(错误日志) 记录服务器运行期间发生的诊断信息和错误的日志文件（例如，`error_log`）。这是排查 500 错误的首要地点。",
    "LogLevel": "Apache 配置指令，用于控制记录在错误日志中的消息的详细程度（例如 `debug`, `info`, `warn`, `error`）。",
    "MPM": "(Multi-Processing Module) 多路处理模块。Apache 用于处理网络连接、接受和处理请求的底层架构。常见的有 `prefork`（每个请求一个进程）、`worker`（多进程多线程）和 `event`（基于事件）。",
    # === Docker 错误与术语 ===
    "ImageNotFound": "(镜像未找到) 错误，表示 Docker 守护进程（Daemon）在本地找不到尝试运行或拉取的镜像（Image），并且在配置的远程仓库（Registry）中也找不到该标签（Tag）。",
    "Container exited (Code 137)": "(容器退出，代码137) 状态码 137 = 128 + 9 (SIGKILL)。这通常意味着容器是被宿主机（Host）的 OOM Killer（内存溢出杀手）强制杀死的，因为容器超出了其内存限制。",
    "Network unreachable": "(网络不可达) 容器内部尝试访问外部网络或宿主机上的其他端口时发生的错误。通常与 Docker 的网络配置（如 `bridge`, `overlay`）或宿主机的防火墙（iptables）规则有关。",
    "Dockerfile": "(Dockerfile) 一个文本文件，包含用于构建（build）Docker 镜像的指令和步骤。",
    "docker-compose": "(Docker Compose) 一个用于定义和运行多容器 Docker 应用程序的工具。它使用 YAML 文件（`docker-compose.yml`）来配置应用的服务。",
    "Volume": "(卷) Docker 用于持久化容器数据的首选机制。卷由 Docker 管理，存储在宿主机的特定目录中（例如 `/var/lib/docker/volumes/`），并且其生命周期独立于容器。",
    "Bind Mount": "(绑定挂载) 另一种持久化数据的方式，将宿主机文件系统上的任意路径挂载到容器中。相比卷，它的灵活性更高，但也更依赖于宿主机的目录结构。",
    "Port conflict": "(端口冲突) 当尝试启动一个容器并将其端口（`--publish` 或 `-p`）映射到宿主机时，如果宿主机的该端口已被其他进程（或另一个容器）占用，则会发生此错误。",
    "Daemon error": "(守护进程错误) 来自 Docker 守护进程（dockerd）的错误。通常需要检查守护进程的日志（例如通过 `journalctl -u docker.service`）来获取详细信息。",
    "Layer": "(层) Docker 镜像是由多个只读层（Layer）堆叠而成的。Dockerfile 中的每一条指令（如 `RUN`, `COPY`, `ADD`）都会创建一个新的层。",
    "OOMKilled": "(因内存溢出被杀死) 见 `Container exited (Code 137)`。在 `docker inspect` 的状态信息中明确显示，表示容器因超出内存限制而被杀死。",
    # === Tomcat 错误与术语 ===
    "java.lang.OutOfMemoryError: Java heap space": "(堆内存溢出) 最常见的 OOM 错误。表示 JVM 的堆内存（用于存储对象实例）已满，并且垃圾收集器（GC）无法释放足够的空间来分配新对象。",
    "java.lang.OutOfMemoryError: PermGen Space": "(永久代溢出) [仅限 Java 7 及以下] 永久代（用于存储类、方法等元数据）已满。",
    "java.lang.OutOfMemoryError: Metaspace": "(元空间溢出) [Java 8+] 替代 PermGen Space 的元空间已满。这通常发生在加载了大量类（例如，应用热部署多次）时。",
    "Connector": "(连接器) Tomcat 中负责处理客户端连接的组件。最常见的是 HTTP/1.1 Connector（默认在 8080 端口）和 AJP Connector（默认在 8009 端口）。",
    "catalina.out": "Tomcat 在 Unix/Linux 系统上的主要日志文件。它默认捕获所有写入标准输出（stdout）和标准错误（stderr）的日志。",
    "localhost_access_log": "(访问日志) Tomcat 记录所有收到的 HTTP 请求的日志，类似于 Apache 的 access_log。",
    "web.xml": "(部署描述符) Web 应用程序的标准配置文件（位于 `WEB-INF/` 目录下），用于定义 Servlet、Filter、Session 超时等。",
    "WAR file": "(Web Application Archive) Web 应用程序的打包格式，本质上是一个 ZIP 文件，包含 Java 类、JSP 文件、库（JARs）和 `web.xml`。",
    "Deployment error": "(部署失败) Tomcat 启动时或热部署 WAR 包时未能成功加载 Web 应用程序。详细原因必须查看 `catalina.out` 或特定于应用程序的日志。",
    "404 Not Found": "(HTTP 404 未找到) Tomcat 无法找到与请求 URL 匹配的资源（Servlet 或静态文件）。这可能是由于 URL 拼写错误，或者应用未成功部署（Context 未加载）。",
    "HTTP 503 Service Unavailable": "(HTTP 503 服务不可用) Tomcat 返回此状态码通常表示服务器正忙，无法处理请求。一个常见原因是在启动时应用尚未完全加载。",
    "maxThreads": "(最大线程数) Connector 配置中的一个重要参数，定义了 Tomcat 可以创建的用于处理请求的最大工作线程数。达到此限制后，新连接会排队。",
    # === C 语言错误与术语 ===
    "Segmentation fault (SIGSEGV)": "(段错误) 信号 11。试图访问无效的内存地址。最常见的原因是解引用空指针（NULL pointer dereference）或已释放的指针（dangling pointer），以及数组越界。",
    "SIGBUS (Bus error)": "(总线错误) 信号 10。通常发生在访问未对齐的内存地址时（例如，在某些架构上尝试将一个 `int*` 指针强转到奇数地址），或访问物理上不存在的内存。",
    "Core dump": "(核心转储) 当程序因致命信号（如 SIGSEGV 或 SIGABRT）而崩溃时，操作系统可以生成一个 `core` 文件。该文件是程序崩溃时内存状态的快照，可用于 `gdb` 等调试器进行事后分析。",
    "malloc": "(内存分配) C 标准库函数，用于在堆（Heap）上动态分配指定字节数的内存。",
    "free": "(内存释放) C 标准库函数，用于释放之前由 `malloc`、`calloc` 或 `realloc` 分配的内存。",
    "Memory Leak": "(内存泄漏) 程序通过 `malloc` 分配了内存，但在使用完毕后未能通过 `free` 释放，导致该内存块丢失引用且无法被重用。",
    "Dangling Pointer": "(悬空指针) 指针指向的内存已经被释放（`free`）或已超出作用域（例如，指向一个局部变量的地址），但该指针本身仍然存在。解引用悬空指针会导致未定义行为。",
    "Buffer Overflow": "(缓冲区溢出) 当向缓冲区（如数组）写入的数据超过了其分配的大小时，多余的数据会覆盖相邻的内存区域。这是许多安全漏洞（如栈溢出）的根源。",
    "Undefined Behavior": "(未定义行为) C 语言标准中未明确定义其结果的操作。例如，有符号整数溢出、解引用空指针、修改字符串字面量等。编译器可以做任何假设，导致程序行为不可预测。",
    "SIGABRT": "(中止信号) 信号 6。通常由程序自己调用 `abort()` 函数触发，表示检测到内部错误或断言（assertion）失败。",
    # === C++ 错误与术语 ===
    "std::bad_alloc": "(内存分配异常) 当 `new` 运算符无法分配所需的内存时抛出的标准异常。",
    "std::exception": "C++ 标准异常类层次结构的基类。`catch(std::exception& e)` 可以捕获大部分标准库异常。",
    "RAII": "(Resource Acquisition Is Initialization) 资源获取即初始化。C++ 的核心编程范式，利用对象的构造函数（Constructor）获取资源（如内存、文件句柄、锁），并在析构函数（Destructor）中释放资源，以确保资源被自动和正确地释放，避免泄漏。",
    "Smart Pointer": "(智能指针) 实践 RAII 范式的类，用于管理动态分配的内存。例如 `std::unique_ptr`（独占所有权）、`std::shared_ptr`（共享所有权）和 `std::weak_ptr`。",
    "nullptr": "C++11 引入的空指针常量，用于替代 C 风格的 `NULL`，具有更强的类型安全性。",
    "Undefined reference": "(未定义引用) 链接器（Linker）错误。表示代码中调用了一个函数或使用了一个变量，该函数或变量只有声明（Declaration）但链接器找不到其定义（Definition）的实现。",
    "Linker error": "(链接器错误) 在编译（Compile）之后、生成可执行文件之前的链接（Link）阶段发生的错误。最常见的是 `Undefined reference`。",
    "vtable": "(虚函数表) C++ 实现多态（Polymorphism）的机制。包含虚函数（virtual function）的类（或其基类）通常会有一个指向 vtable 的指针（vptr）。vtable 是一个函数指针数组，用于在运行时解析应调用的虚函数版本。",
    "std::terminate": "当异常未被捕获（no-catch）时，或在析构函数中抛出异常时，C++ 运行时会调用的函数，默认行为是调用 `abort()` 终止程序。",
    "OOM": "(Out of Memory) 内存溢出。在 C++ 中，这通常表现为 `new` 抛出 `std::bad_alloc` 异常。",
    "SIGSEGV": "(段错误) 见 C 语言部分。在 C++ 中同样常见，原因包括解引用 `nullptr`、悬空指针或访问越界的 `std::vector`。",
    # === Go 语言错误与术语 ===
    "nil pointer dereference": "(nil 指针解引用) Go 运行时 panic。当程序试图访问一个值为 `nil` 的指针、切片（slice）、映射（map）、通道（channel）或接口（interface）的成员或方法时发生。",
    "goroutine": "(协程) Go 语言并发（Concurrency）的执行单位。它是由 Go 运行时管理的轻量级线程。",
    "channel": "(通道) Go 中用于在 goroutine 之间通信和同步的数据结构。",
    "fatal error: all goroutines are asleep - deadlock!": "(致命错误：所有 goroutine 均已休眠 - 死锁！) Go 运行时检测到死锁。这通常发生在主 goroutine 被阻塞（例如等待一个永远不会有数据的 channel），而没有其他 goroutine 在运行时。",
    "context deadline exceeded": "(上下文截止日期超出) `context.Context` 是 Go 中用于控制超时和取消（Cancellation）的标准模式。当一个操作的执行时间超过了其 `Context` 设定的截止时间（Deadline）或超时（Timeout）时，会返回此错误。",
    "panic": "Go 语言中的一种运行时异常机制。当发生不可恢复的错误（如 `nil pointer dereference`）时，程序会 `panic`。",
    "recover": "Go 中的一个内置函数，仅在 `defer` 语句中有效。用于捕获 `panic`，使程序从 `panic` 状态恢复并继续执行。",
    "GOMAXPROCS": "(最大处理器数) 环境变量或运行时参数，用于设置 Go 程序可以同时运行（在操作系统线程上）的 goroutine 的最大数量。",
    "GC": "(Garbage Collector) 垃圾收集器。Go 语言自带内存管理，其 GC 负责自动回收不再被引用的内存。",
    "slice index out of range": "(切片索引越界) panic，当尝试访问的切片索引小于 0 或大于等于切片长度（`len()`）时发生。",
    "send on closed channel": "(向已关闭的通道发送) panic，当一个 goroutine 尝试向一个已经关闭（`close`）的 channel 发送数据时发生。",
    "close of nil channel": "(关闭 nil 通道) panic，尝试关闭一个未初始化（`nil`）的 channel。",
    # === Java 语言错误与术语 ===
    "NullPointerException (NPE)": "(空指针异常) Java 中最常见的运行时异常（`RuntimeException`）。当程序试图访问或调用一个值为 `null` 的对象的成员变量或方法时抛出。",
    "OutOfMemoryError (OOM)": "(内存溢出错误) `java.lang.OutOfMemoryError`。这是一个 `Error`（而非 `Exception`），表示 JVM 内存耗尽。最常见的类型是 `Java heap space`（堆空间溢出）和 `Metaspace`（元空间溢出）。",
    "ClassNotFoundException": "(类未找到异常) 这是一个受检异常（Checked Exception）。通常发生在使用反射（Reflection）如 `Class.forName()` 或动态加载类时，在运行时（Classpath）中找不到该类的 `.class` 文件。",
    "NoClassDefFoundError": "(无类定义错误) 这是一个 `Error`。它发生在 JVM 在编译时能找到该类，但在运行时（当实际尝试使用该类时）该类却不可用。这通常是由于类路径（Classpath）配置问题或 JAR 包冲突。",
    "StackOverflowError": "(栈溢出错误) `java.lang.StackOverflowError`。当一个方法的调用深度过深时（例如，一个没有终止条件的递归调用）抛出，导致 JVM 栈（Stack）空间耗尽。",
    "Garbage Collection (GC)": "(垃圾收集) JVM 自动内存管理的核心。GC 负责识别和回收堆（Heap）中不再被引用的对象所占用的内存。",
    "JVM": "(Java Virtual Machine) Java 虚拟机。运行 Java 字节码（`.class` 文件）的抽象计算机。",
    "Heap": "(堆) JVM 内存中最大的一块区域，用于存储所有对象实例和数组。",
    "SQLException": "(SQL 异常) Java 访问数据库（JDBC）时，所有数据库相关错误的基类异常。",
    "ConcurrentModificationException": "(并发修改异常) 当在迭代（Iterate）一个集合（Collection）的同时，又在（非迭代器本身的方法）修改该集合（如添加或删除元素）时，可能会抛出此异常。这是一种快速失败（fail-fast）机制。",
    "ClassLoader": "(类加载器) JVM 中负责查找和加载 `.class` 文件到内存中，并将其转换为 `Class` 对象的组件。",
    "JAR": "(Java Archive) Java 归档文件，一种基于 ZIP 格式的文件包，用于分发 Java 类、元数据和资源（如图片）。",
    # === Python 语言错误与术语 ===
    "IndentationError": "(缩进错误) Python 语法错误的一种。当代码块的缩进（使用空格或制表符）不正确或不一致时引发。",
    "KeyError": "(键错误) 当试图访问字典（`dict`）中一个不存在的键（Key）时引发的异常。",
    "AttributeError": "(属性错误) 当试图访问或赋值一个对象上不存在的属性（Attribute）或方法（Method）时引发。",
    "TypeError": "(类型错误) 当对一个对象执行了其类型不支持的操作时引发。例如，将字符串（`str`）和整数（`int`）相加。",
    "ValueError": "(值错误) 当传递给函数或方法的参数类型正确，但值不合适时引发。例如，`int('abc')`。",
    "NameError": "(名称错误) 当使用一个未被定义（未被赋值）的局部或全局变量名时引发。",
    "ImportError / ModuleNotFoundError": "(导入错误 / 模块未找到) 当 `import` 语句无法找到指定的模块（Python 2 中为 `ImportError`，Python 3.6+ 中为 `ModuleNotFoundError`）或无法从模块中导入指定的名称时引发。",
    "GIL": "(Global Interpreter Lock) 全局解释器锁。CPython（标准 Python 解释器）中的一个机制，该锁确保同一时间只有一个线程能执行 Python 字节码。这简化了内存管理，但也限制了 Python 在多核 CPU 上的并发性能。",
    "virtualenv / venv": "(虚拟环境) 用于创建独立的 Python 运行环境的工具。它允许不同项目使用不同版本的库，避免依赖冲突。",
    "pip": "(Pip Installs Packages) Python 的标准包管理器，用于安装和管理 Python 包（通常来自 PyPI）。",
    "Traceback": "(回溯) 当 Python 程序中发生未捕获的异常时，解释器打印出的错误报告，显示了从异常发生点到程序顶层的函数调用栈。",
    "FileNotFoundError": "(文件未找到) `IOError` 的一个子类。当尝试打开一个不存在的文件进行读操作时引发。",
    # === Kafka 术语 ===
    "Broker": "(代理) Kafka 集群中的一个服务器实例。一个 Broker 负责存储数据（Topic 的 Partition）、处理来自 Producer 的写入请求和来自 Consumer 的读取请求。",
    "Topic": "(主题) Kafka 中消息的类别或分类名称。Producer 将消息发布到特定的 Topic，Consumer 订阅 Topic 来消费消息。",
    "Partition": "(分区) Topic 的物理分组。一个 Topic 可以被分成一个或多个 Partition。每个 Partition 是一个有序的、不可变的日志（Log）文件。Partition 是 Kafka 实现并行处理和扩展性的关键。",
    "Producer": "(生产者) 向 Kafka Topic 发布（写入）消息的客户端应用程序。",
    "Consumer": "(消费者) 从 Kafka Topic 订阅（读取）消息的客户端应用程序。",
    "Consumer Group": "(消费者组) 由一个或多个 Consumer 实例组成的组，它们共同消费一个或多个 Topic。一个 Topic 的同一个 Partition 只能被组内的某一个 Consumer 实例消费，以此实现负载均衡和容错。",
    "ZooKeeper": "(ZooKeeper) [在 Kafka 早期版本中必须，新版本中正在被移除] 一个分布式的协调服务。Kafka 曾使用它来管理 Broker、选举 Controller、存储 Topic 配置和管理 Consumer Group。",
    "Replication Factor": "(复制因子) 定义了一个 Topic 的每个 Partition 在集群中有多少个副本（Replica）。例如，复制因子为 3 表示有 1 个 Leader 和 2 个 Follower。",
    "ISR (In-Sync Replicas)": "(同步副本列表) Partition 的副本（Replica）集合中，那些与 Leader 保持同步（即数据延迟在一定阈值内）的 Follower 副本。",
    "Leader": "(领导者) 每个 Partition 的所有副本中，只有一个是 Leader。所有 Producer 的写入和 Consumer 的读取请求都只由 Leader 处理。",
    "Follower": "(跟随者) Partition 副本中非 Leader 的其他副本。它们被动地从 Leader 拉取数据，以保持同步。",
    "Rebalance": "(重均衡) 当 Consumer Group 中的成员（Consumer 实例）发生变化（例如有新的 Consumer 加入、旧的 Consumer 掉线）时，Kafka 会重新分配 Partition 给组内的 Consumer。这个过程称为 Rebalance。",
    # === Nginx 错误与术语 ===
    "502 Bad Gateway": "(HTTP 502 错误网关) Nginx 作为反向代理（Reverse Proxy）时最常见的错误。表示 Nginx 成功连接到了上游（Upstream）服务器（如 Tomcat, uWSGI），但从上游服务器收到了一个无效的、错误的或无法解析的响应。",
    "504 Gateway Timeout": "(HTTP 504 网关超时) Nginx 作为反向代理时，连接到了上游服务器，但上游服务器在 Nginx 配置的超时时间（如 `proxy_read_timeout`）内没有返回任何响应。",
    "upstream": "(上游) Nginx 配置块，用于定义一组后端服务器。Nginx 会将请求（通过 `proxy_pass`）负载均衡到这个组中的服务器。",
    "proxy_pass": "Nginx 的核心指令之一，用于将请求转发到 `http://` 或 `https://` 定义的后端服务器或 `upstream` 组。",
    "location": "Nginx 配置块，用于根据请求的 URI（URL 路径）来匹配不同的配置规则。",
    "server_name": "Nginx 指令，用于定义此 `server` 块应处理哪些主机名（域名）的请求。",
    "worker_processes": "Nginx 的主配置指令，定义了 Nginx 启动的 worker 进程数。通常设置为 CPU 核心数。",
    "403 Forbidden": "(HTTP 403 禁止) Nginx 拒绝了请求。常见原因包括：(1) 目录启用了 `autoindex off` 但没有 `index` 文件；(2) 文件系统权限（Nginx worker 进程的用户无权读取文件）；(3) `allow` / `deny` 指令限制了 IP。",
    "root": "Nginx 指令，定义了请求的根目录。例如，请求 `/image.png` 且 `root /var/www/html;`，Nginx 会查找 `/var/www/html/image.png`。",
    "alias": "Nginx 指令，与 `root` 类似，但它会替换匹配到的 `location` 路径。",
    "try_files": "Nginx 指令，按顺序检查指定的文件或目录是否存在。如果都找不到，通常会内部重定向到最后一个参数（例如，`try_files $uri $uri/ /index.php?$query_string;` 是 PHP-FPM 的典型配置）。",
    "499 Client Closed Request": "(HTTP 499) Nginx 特有的状态码。表示客户端（如浏览器）在 Nginx 尚未完成响应时主动关闭了连接。",
    # === RabbitMQ 术语 ===
    "Exchange": "(交换机) RabbitMQ 消息模型的四大核心组件之一。Producer（生产者）将消息发布到 Exchange。Exchange 收到消息后，根据其类型（如 `direct`, `topic`, `fanout`）和路由键（Routing Key）将消息路由到一个或多个 Queue（队列）。",
    "Queue": "(队列) RabbitMQ 中存储消息的缓冲区。Consumer（消费者）从 Queue 中获取消息。",
    "Binding": "(绑定) Exchange 和 Queue 之间的连接（或 Exchange 与 Exchange 之间的连接）。它定义了 Exchange 如何根据路由键将消息路由到 Queue。",
    "Routing Key": "(路由键) Producer 发送消息到 Exchange 时指定的元数据。Binding 会检查 Routing Key 以决定是否将消息转发到其绑定的 Queue。",
    "AMQP": "(Advanced Message Queuing Protocol) 高级消息队列协议。RabbitMQ 实现了 AMQP 0-9-1 规范，这是一个开放的消息传递标准。",
    "vhost": "(Virtual Host) 虚拟主机。在 RabbitMQ 中，vhost 提供了逻辑上的隔离。每个 vhost 就像一个独立的 RabbitMQ 服务器，拥有自己的 Exchange、Queue 和权限。",
    "Message ACK": "(消息确认) 当 Consumer 确认已成功处理一条消息后，向 RabbitMQ 发送的确认信号（`basic.ack`）。收到 ACK 后，RabbitMQ 才会将该消息从队列中删除。",
    "NACK": "(消息否认) Consumer 告诉 RabbitMQ 它无法处理某条消息（`basic.nack` 或 `basic.reject`）。RabbitMQ 可以选择重新排队该消息或将其丢弃/发送到死信队列。",
    "Dead Letter Exchange (DLX)": "(死信交换机) 一个普通的 Exchange，用于接收那些“死亡”的消息（例如，被 NACK 且未重排队、TTL 过期、队列已满）。",
    "High Watermark": "(高水位线) RabbitMQ 的流控（Flow Control）机制。当 Broker 检测到内存或磁盘使用达到设定的阈值（High Watermark）时，它会阻塞 Producer 的连接，暂停接收新消息，以防止系统崩溃。",
}


def api_key_auth(request):
    """验证请求头中的API Key"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    try:
        scheme, key = auth_header.split()
        if scheme.lower() != "bearer":
            return None
        api_key = APIKey.objects.get(key=key)
        return api_key
    except (ValueError, APIKey.DoesNotExist):
        return None


router = Router(auth=api_key_auth)


def clean_llm_reply(reply: str) -> str:
    """
    从 DeepSeek-R1:7B 的原始回复中移除 <think>...</think> 标签块

    DeepSeek-R1 模型的思考过程被包裹在 <think> 标签中，
    此函数用于清理这些思考过程，只保留最终的用户可见回复。
    """
    # re.DOTALL 使 '.' 能够匹配包括换行符在内的任意字符
    return re.sub(r"<think>.*?</think>\s*", "", reply, flags=re.DOTALL).strip()


@api.post("/login", response={200: LoginOut, 400: ErrorResponse, 403: ErrorResponse})
def login(request, data: LoginIn):
    username = data.username.strip()
    password = data.password.strip()
    if not username or not password:
        return 400, {"error": "用户名和密码不能为空"}
    if password != "secret":
        return 403, {"error": "密码错误"}
    key = services.create_api_key(username)
    return {"api_key": key, "expiry": settings.TOKEN_EXPIRY_SECONDS}


@router.post("/chat")
def chat(request, data: ChatIn):
    if not request.auth:
        return StreamingHttpResponse(
            "data: "
            + json.dumps({"type": "error", "chunk": "请先登录获取API Key"})
            + "\n\n",
            status=401,
            content_type="text/event-stream",
        )

    session_id = data.session_id.strip() or "默认对话"
    user_input = data.user_input.strip()
    if not user_input:
        return StreamingHttpResponse(
            "data: "
            + json.dumps({"type": "error", "chunk": "请输入消息内容"})
            + "\n\n",
            status=400,
            content_type="text/event-stream",
        )

    user = request.auth
    session = get_or_create_session(session_id, user)

    # 获取搜索选项
    use_db_search = data.use_db_search
    use_web_search = data.use_web_search
    selected_model = data.model_name
    logger.info(f"搜索选项 - 数据库: {use_db_search}, 联网: {use_web_search}")
    if selected_model:
        logger.info(f"前端请求使用模型: {selected_model}")

    if data.context and len(data.context) > 0:
        # 情况A：前端提供了 context，使用它作为对话历史
        logger.info(
            f"使用前端提供的 context (会话: {session_id}, 上下文长度: {len(data.context)})"
        )
        history_for_llm = data.context
        is_regeneration = False  # 前端已经处理了截断，不需要重新生成检测
    else:
        # 情况B：前端没有提供 context，回退到从数据库加载历史
        conversation_history = session.get_conversation_history()

        history_for_llm = conversation_history
        is_regeneration = False

        if (
            len(conversation_history) >= 2
            and conversation_history[-1]["role"] == "assistant"
            and conversation_history[-2]["role"] == "user"
            and conversation_history[-2]["content"] == user_input
        ):

            logger.info(f"检测到重新生成 (会话: {session_id})")
            history_for_llm = conversation_history[:-2]
            is_regeneration = True

        elif (
            len(conversation_history) >= 1
            and conversation_history[-1]["role"] == "user"
            and conversation_history[-1]["content"] == user_input
        ):

            logger.info(f"检测到对失败消息的重新生成 (会话: {session_id})")
            history_for_llm = conversation_history[:-1]  # 移除 Q_last
            is_regeneration = True

    def stream_generator() -> Generator[str, None, None]:
        buffer = ""
        is_thinking = False
        full_clean_reply = ""  # 用于最后存入数据库

        start_time = time.time()  # 在开始迭代前计时
        think_time_sent = False  # 确保元数据只发送一次
        print("History\n", history_for_llm)
        try:
            for raw_chunk in model_api_call(
                user_input,
                history_for_llm,
                use_db_search,
                use_web_search,
                model_name=selected_model,
            ):
                buffer += raw_chunk

                while True:
                    if not is_thinking:
                        start_index = buffer.find("<think>")
                        if start_index != -1:
                            before = buffer[:start_index]
                            if before:
                                yield "data: " + json.dumps(
                                    {"type": "content", "chunk": before}
                                ) + "\n\n"
                                full_clean_reply += before
                            buffer = buffer[start_index + len("<think>") :]
                            is_thinking = True
                            continue
                        else:
                            if buffer:
                                yield "data: " + json.dumps(
                                    {"type": "content", "chunk": buffer}
                                ) + "\n\n"
                                full_clean_reply += buffer
                                buffer = ""
                            break
                    if is_thinking:
                        end_index = buffer.find("</think>")
                        if end_index != -1:
                            if not think_time_sent:
                                end_think_time = time.time()
                                duration = round(end_think_time - start_time, 2)
                                yield "data: " + json.dumps(
                                    {"type": "metadata", "duration": duration}
                                ) + "\n\n"
                                think_time_sent = True

                            think_chunk = buffer[:end_index]
                            if think_chunk:
                                yield "data: " + json.dumps(
                                    {"type": "think", "chunk": think_chunk}
                                ) + "\n\n"

                            buffer = buffer[end_index + len("</think>") :]
                            is_thinking = False
                            continue
                        else:
                            if buffer:
                                yield "data: " + json.dumps(
                                    {"type": "think", "chunk": buffer}
                                ) + "\n\n"
                                buffer = ""
                            break

            # (循环结束) 处理剩余缓冲区
            if is_thinking and buffer:
                yield "data: " + json.dumps({"type": "think", "chunk": buffer}) + "\n\n"
            elif buffer:
                yield "data: " + json.dumps(
                    {"type": "content", "chunk": buffer}
                ) + "\n\n"
                full_clean_reply += buffer

            # 流全部结束后，更新数据库
            try:
                final_save = clean_llm_reply(full_clean_reply).strip()

                # 检查是否使用了前端提供的 context（编辑模式）
                if data.context and len(data.context) > 0:
                    # 编辑模式：前端已经截断了历史，我们需要重写整个上下文
                    # 格式化为 "\n用户：{q}\n回复：{a}\n" 格式
                    new_context_str = ""
                    # 添加前端提供的截断后的历史
                    for msg in history_for_llm:
                        if msg["role"] == "user":
                            new_context_str += f"\n用户：{msg['content']}\n"
                        elif msg["role"] == "assistant":
                            new_context_str += f"\n回复：{msg['content']}\n"

                    # 添加当前轮次的新回复（编辑后的提问 + 新的 AI 回答）
                    new_context_str += f"\n用户：{user_input}\n"
                    new_context_str += f"\n回复：{final_save}\n"

                    # 重写数据库上下文
                    session.context = new_context_str.strip()
                    session.save()
                    logger.info(
                        f"编辑模式：会话 {session_id} 已更新 (用户: {user.user})"
                    )

                elif is_regeneration:

                    new_context_str = ""
                    # 重新组合截断的历史
                    for msg in history_for_llm:
                        if msg["role"] == "user":
                            new_context_str += f"\n用户：{msg['content']}\n"
                        elif msg["role"] == "assistant":
                            new_context_str += f"\n回复：{msg['content']}\n"

                    # 添加当前轮次的新回复
                    new_context_str += f"\n用户：{user_input}\n"
                    new_context_str += f"\n回复：{final_save}\n"

                    # (假设 session.context 是可写的)
                    session.context = new_context_str.strip()
                    session.save()

                else:
                    # 正常追加 (调用 models.py 中的方法)
                    session.update_context(user_input, final_save)

                logger.info(f"会话 {session_id} 已更新 (用户: {user.user})")
            except Exception as e:
                logger.error(f"数据库上下文更新失败: {e}")

        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            yield "data: " + json.dumps(
                {"type": "error", "chunk": f"流处理失败: {e}"}
            ) + "\n\n"

    # 返回 StreamingHttpResponse
    response = StreamingHttpResponse(
        stream_generator(), content_type="text/event-stream"  # (修改) SSE
    )
    # 禁用 Nginx 缓冲
    response["X-Accel-Buffering"] = "no"
    return response


@router.get("/history", response={200: HistoryOut})
def history(request, session_id: str = "默认对话"):
    processed_session_id = session_id.strip() or "默认对话"
    session = services.get_or_create_session(processed_session_id, request.auth)
    return {"history": session.context}


@router.delete("/history", response={200: dict})
def clear_history(request, session_id: str = "默认对话"):
    processed_session_id = session_id.strip() or "默认对话"
    session = services.get_or_create_session(processed_session_id, request.auth)
    session.clear_context()
    return {"message": "历史记录已清空"}


@router.get("/glossary", response={200: dict})
def get_glossary(request):
    """返回前端使用的术语解释词典"""
    return {"terms": GLOSSARY_ENTRIES}


api.add_router("", router)


# 新增：文件上传解析接口
@router.post("/upload_file")
def upload_file(request, file: NinjaUploadedFile = File(...)):
    if not request.auth:
        return 401, {"error": "请先登录获取API Key"}

    filename = (file.name or "").lower()
    try:
        if filename.endswith(".txt"):
            # 纯文本
            content_bytes = file.read()
            try:
                text = content_bytes.decode("utf-8")
            except Exception:
                text = content_bytes.decode("gbk", errors="ignore")
            return {"text": text}

        elif filename.endswith(".docx"):
            try:
                from docx import Document
            except Exception:
                return 400, {"error": "缺少依赖：请安装 python-docx"}

            document = Document(file)
            paragraphs = [p.text for p in document.paragraphs if p.text]
            text = "\n".join(paragraphs)
            return {"text": text}

        elif filename.endswith(".xlsx"):
            try:
                import openpyxl
            except Exception:
                return 400, {"error": "缺少依赖：请安装 openpyxl"}

            wb = openpyxl.load_workbook(file, data_only=True)
            lines = []
            for ws in wb.worksheets:
                lines.append(f"# 工作表: {ws.title}")
                for row in ws.iter_rows(values_only=True):
                    # 将每行的单元格以制表符连接
                    cells = ["" if v is None else str(v) for v in row]
                    lines.append("\t".join(cells))
            text = "\n".join(lines)
            return {"text": text}

        else:
            return 400, {"error": "不支持的文件类型，仅支持 .txt / .docx / .xlsx"}

    except Exception as e:
        logger.error(f"文件解析失败: {e}")
        return 400, {"error": f"文件解析失败: {e}"}
