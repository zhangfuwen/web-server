# 祝福/禅语发布与评论系统 (Blessings API)

为修心应用第一个 tab（正念）设计的发布和评论功能。

## 📍 访问地址

- **Web 测试页面**: http://bot.xjbcode.fun/blessings
- **API 基础路径**: http://bot.xjbcode.fun:8081/api/blessings

## 🗄️ 数据库

- **路径**: `/var/www/html/data/blessings.db`
- **表结构**:
  - `blessings`: 祝福/禅语主表
  - `comments`: 评论表
  - `blessing_interactions`: 用户互动记录（点赞/收藏）

## 📡 API Endpoints

### 祝福/禅语 CRUD

```bash
# 获取列表 (支持分页和分类筛选)
GET /api/blessings?limit=20&offset=0&category=禅宗

# 获取单个
GET /api/blessings/{id}

# 创建新祝福
POST /api/blessings
Content-Type: application/json
{
  "user_id": "user-123",
  "user_name": "张三",
  "text": "禅语内容",
  "source": "出处",
  "practice": "今日练习",
  "category": "禅宗"
}

# 更新 (仅所有者)
PUT /api/blessings/{id}
Content-Type: application/json
{
  "user_id": "user-123",
  "text": "更新后的内容"
}

# 删除 (软删除，仅所有者)
DELETE /api/blessings/{id}
Content-Type: application/json
{
  "user_id": "user-123"
}
```

### 评论功能

```bash
# 获取评论列表
GET /api/blessings/{id}/comments?limit=50&offset=0

# 添加评论
POST /api/blessings/{id}/comments
Content-Type: application/json
{
  "user_id": "user-456",
  "user_name": "李四",
  "content": "评论内容",
  "parent_id": null  // 可选，回复评论时填写父评论 ID
}
```

### 互动功能

```bash
# 点赞 (切换)
POST /api/blessings/{id}/like
Content-Type: application/json
{
  "user_id": "user-123"
}

# 收藏 (切换)
POST /api/blessings/{id}/favorite
Content-Type: application/json
{
  "user_id": "user-123"
}
```

### 统计信息

```bash
# 获取整体统计
GET /api/blessings/stats

# 响应示例
{
  "success": true,
  "data": {
    "total_blessings": 42,
    "total_comments": 128,
    "by_category": {
      "禅宗": 25,
      "儒家": 8,
      "道家": 6,
      "佛经": 3
    },
    "top_liked": [...]
  }
}
```

## 📱 Android 集成

Android 应用可以通过 HTTP 请求调用 API，替换当前的硬编码数据。

### 示例代码 (Kotlin)

```kotlin
// 获取禅语列表
suspend fun loadBlessings(category: String = "全部"): List<Blessing> {
    val url = if (category == "全部") {
        "$API_BASE/blessings?limit=20"
    } else {
        "$API_BASE/blessings?limit=20&category=$category"
    }
    
    val response = httpClient.get(url)
    val json = Json.parseToJsonElement(response.body).jsonObject
    val data = json["data"]!!.jsonArray
    
    return data.map { item ->
        Blessing(
            id = item["id"]!!.int,
            text = item["text"]!!.string,
            source = item["source"]?.string ?: "",
            practice = item["practice"]?.string ?: "",
            category = item["category"]!!.string,
            likeCount = item["like_count"]!!.int,
            favoriteCount = item["favorite_count"]!!.int,
            isLiked = item["is_liked"]?.boolean ?: false,
            isFavorited = item["is_favorited"]?.boolean ?: false
        )
    }
}

// 发布新禅语
suspend fun publishBlessing(text: String, source: String, practice: String, category: String) {
    val payload = Json.buildJsonObject {
        put("user_id", userId)
        put("user_name", userName)
        put("text", text)
        put("source", source)
        put("practice", practice)
        put("category", category)
    }
    
    httpClient.post("$API_BASE/blessings") {
        contentType(ContentType.Application.Json)
        setBody(payload)
    }
}
```

## 🎨 分类系统

支持以下分类：
- **禅宗**: 禅宗公案、禅师语录
- **儒家**: 四书五经、儒家经典
- **道家**: 道德经、庄子等
- **佛经**: 金刚经、楞严经等佛经

## 🔐 权限说明

当前版本为简化版：
- 任何用户都可以发布内容
- 只有发布者可以编辑/删除自己的内容
- 通过 `user_id` 简单验证所有权
- 后续可集成完整认证系统

## 🚀 后续优化

1. **迁移到独立服务**: 当前在 molt_server 中，后续可独立部署
2. **完整认证系统**: 集成 OAuth 或 JWT
3. **内容审核**: 添加举报和审核机制
4. **搜索功能**: 全文搜索禅语内容
5. **推荐算法**: 基于用户喜好推荐禅语
6. **WebSocket 实时通知**: 新评论/点赞实时推送

## 📝 开发日志

- **2026-03-14**: 初始版本完成
  - 数据库设计和实现
  - RESTful API 完整实现
  - Web 测试页面
  - 初始数据种子 (10 条经典禅语)
  - Git 提交：f596055
