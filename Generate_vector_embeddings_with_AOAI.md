[翻訳元](https://microsoftlearning.github.io/mslearn-postgresql/Instructions/Labs/13-generate-vector-embeddings-azure-openai.html)

# Azure OpenAI を使用してベクター埋め込みを生成する

セマンティック検索を実行するには、まずモデルから埋め込みベクターを生成し、ベクターデータベースに格納してから、埋め込みをクエリする必要があります。データベースを作成し、サンプルデータを設定して、それらのリストに対してセマンティック検索を実行します。

この演習の終わりまでに、`vector` 拡張機能と `azure_ai` 拡張機能が有効になっている Azure Database for PostgreSQL Flexible Server インスタンスが作成されます。[Seattle Airbnb Open Data](https://www.kaggle.com/datasets/airbnb/seattle?select=listings.csv) データセットのリストテーブルの埋め込みを生成します。また、クエリの埋め込みベクターを生成し、ベクターコサイン距離検索を実行することで、これらのリストに対してセマンティック検索を実行します。

## はじめに

管理者権限を持つ [Azure サブスクリプション](https://azure.microsoft.com/free)が必要であり、そのサブスクリプションで Azure OpenAI にアクセスすることが承認されている必要があります。Azure OpenAI へのアクセスが必要な場合は、[Azure OpenAI の制限付きアクセス](https://learn.microsoft.com/legal/cognitive-services/openai/limited-access)ページで申請してください。

### リソースを Azure サブスクリプションにデプロイする

この手順では、Azure Cloud Shell から Azure CLI コマンドを使用してリソース グループを作成し、Bicep スクリプトを実行して、この演習を完了するために必要な Azure サービスを Azure サブスクリプションにデプロイする方法について説明します。

> [!NOTE]
> このラーニングパスで複数のモジュールを実行している場合は、モジュール間で Azure 環境を共有できます。その場合は、このリソースのデプロイ手順を1回だけ完了する必要があります。

1. Web ブラウザーを開き、[Azure portal](https://portal.azure.com/) に移動します。

2. Azure portal ツールバーの \[**Cloud Shell**\] アイコンを選択して、ブラウザー ウィンドウの下部にある新しい [Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/overview) ウィンドウを開きます。

![Cloud Shell Tool Bar](12-portal-toolbar-cloud-shell.png)

3. Cloud Shell プロンプトで、次のように入力して、演習用のリソースを含む GitHub リポジトリを複製します:

```bash
git clone https://github.com/MicrosoftLearning/mslearn-postgresql.git
```

4. 次に、3つのコマンドを実行して変数を定義し、Azure CLI コマンドを使用して Azure リソースを作成する際の冗長な入力を減らします。変数は、リソースグループに割り当てる名前 (`RG_NAME`)、リソースがデプロイされる Azure リージョン (`REGION`)、PostgreSQL 管理者ログイン用にランダムに生成されたパスワード (`ADMIN_PASSWORD`) を表します。

最初のコマンドでは、対応する変数に割り当てられた領域は `eastus` ですが、好みの場所に置き換えることもできます。ただし、既定値を置き換える場合は、[抽象的な概要作成をサポートする別の Azure リージョン](https://learn.microsoft.com/azure/ai-services/language-service/summarization/region-support)を選択して、このラーニングパスのモジュールのすべてのタスクを完了できるようにする必要があります。

```bash
REGION=eastus
```

次のコマンドは、この演習で使用するすべてのリソースを格納するリソースグループに使用する名前を割り当てます。対応する変数に割り当てられるリソースグループ名は `rg-learn-postgresql-ai-$REGION` で`REGION` は上記で指定した場所です。ただし、好みに合った他のリソースグループ名に変更できます。

```bash
RG_NAME=rg-learn-postgresql-ai-$REGION
```

最後のコマンドは、PostgreSQL 管理者ログインのパスワードをランダムに生成します。後で PostgreSQL Flexible Server に接続するときに使用するために、安全な場所にコピーします。

```bash
a=()
for i in {a..z} {A..Z} {0..9}; 
    do
    a[$RANDOM]=$i
done
ADMIN_PASSWORD=$(IFS=; echo "${a[*]::18}")
echo "Your randomly generated PostgreSQL admin user's password is:"
echo $ADMIN_PASSWORD
```

5. 複数の Azure サブスクリプションにアクセスでき、既定のサブスクリプションが、この演習のリソースグループやその他のリソースを作成するサブスクリプションではない場合は、次のコマンドを実行して適切なサブスクリプションを設定し、`<subscriptionName|subscriptionId>` トークンを使用するサブスクリプションの名前または ID に置き換えます:

```bash
az account set --subscription <subscriptionName|subscriptionId>
```

6. 次の Azure CLI コマンドを実行して、リソースグループを作成します:

```bash
az group create --name $RG_NAME --location $REGION
```

7. 最後に、Azure CLI を使用して Bicep デプロイスクリプトを実行し、リソースグループに Azure リソースをプロビジョニングします:

```bash
az deployment group create --resource-group $RG_NAME --template-file "mslearn-postgresql/Allfiles/Labs/Shared/deploy.bicep" --parameters restore=false adminLogin=pgAdmin adminLoginPassword=$ADMIN_PASSWORD
```

Bicep デプロイ スクリプトは、この演習を完了するために必要な Azure サービスをリソースグループにプロビジョニングします。デプロイされるリソースには、Azure Database for PostgreSQL Flexible Server、Azure OpenAI、Azure AI 言語サービスが含まれます。また、Bicep スクリプトでは、PostgreSQL サーバーの許可リストへの `azure_ai` 拡張機能と `vector` 拡張機能の追加 (azure.extensions サーバーパラメーターを使用)、サーバー上に `rentals` という名前のデータベースを作成し、`text-embedding-ada-002` モデルを使用する `embedding` という名前のデプロイを Azure OpenAI サービスに追加するなど、いくつかの構成手順も実行されます。Bicep ファイルは、このラーニングパスのすべてのモジュールで共有されるため、一部の演習ではデプロイされたリソースの一部のみを使用できます。

通常、デプロイが完了するまでに数分かかります。Cloud Shell から監視するか、上記で作成したリソースグループの \[**デプロイ**\] ページに移動して、そこでデプロイの進行状況を確認できます。

Bicep デプロイスクリプトの実行時にいくつかのエラーが発生する場合があります。最も一般的なメッセージとその解決手順は次のとおりです:

* Azure AI Services リソースを以前に作成していない場合は、責任ある AI の利用条件が演習で用いるサブスクリプションで未読で同意されていないというメッセージが表示されることがあります:

```
{"code": "ResourceKindRequireAcceptTerms",
"message": "This subscription cannot create TextAnalytics until you agree to Responsible AI terms for this resource.
You can agree to Responsible AI terms by creating a resource through the Azure Portal and trying again."}
```

このエラーを解決するには、Azure portal から最初の言語リソースを作成し、使用条件を確認して承認できるようにする必要があります。ここで行うことができます: [https://portal.azure.com/#create/Microsoft.CognitiveServicesTextAnalytics](https://portal.azure.com/#create/Microsoft.CognitiveServicesTextAnalytics). ランダムで有効な名前を持つ新しいリソースグループの下に作成し、デプロイする言語サービスにランダムで有効な名前を割り当てます。その後、サブスクリプション全体の責任ある AI の条項に同意すると、同じ Azure サブスクリプションで任意のデプロイツール (SDK、CLI、ARM テンプレートなど) を使用して、後続の言語リソースを作成できます。そのため、ポータルで最初のリソースを作成したら、それを削除し、コマンドを再実行して Bicep デプロイスクリプトを実行できます。

* このラーニングパスの Bicep デプロイ スクリプトを以前に実行し、その後リソースを削除した場合、リソースを削除してから 48 時間以内にスクリプトを再実行しようとすると、次のようなエラー メッセージが表示されることがあります:

```
{"code": "InvalidTemplateDeployment",
"message": "The template deployment 'deploy' is not valid according to the validation procedure.
The tracking id is '4e87a33d-a0ac-4aec-88d8-177b04c1d752'. See inner errors for details."}

Inner Errors:
{"code": "FlagMustBeSetForRestore",
"message": "An existing resource with ID
'/subscriptions/{subscriptionId}/resourceGroups/rg-learn-postgresql-ai-eastus/providers/Microsoft.CognitiveServices/accounts/{accountName}'
has been soft-deleted.
To restore the resource, you must specify 'restore' to be 'true' in the property.
If you don't want to restore existing resource, please purge it first."}
```

このメッセージが表示された場合は、上記の `azure deployment group create` コマンドを変更して、`restore` パラメーターを `true` に設定して再実行します。

* 選択したリージョンで特定のリソースのプロビジョニングが制限されている場合は、`REGION` 変数を別の場所に設定し、Bicep デプロイ スクリプトを再実行する必要があります。

```
{"status":"Failed",
"error":{"code":"DeploymentFailed",
"target":"/subscriptions/{subscriptionId}/resourceGroups/{resourceGrouName}/providers/Microsoft.Resources/deployments/{deploymentName}",
"message":"At least one resource deployment operation failed.
Please list deployment operations for details.
Please see https://aka.ms/arm-deployment-operations for usage details.",
"details":[{"code":"ResourceDeploymentFailure",
"target":"/subscriptions/{subscriptionId}/resourceGroups/{resourceGrouName}/providers/Microsoft.DBforPostgreSQL/flexibleServers/{serverName}",
"message":"The resource write operation failed to complete successfully, because it reached terminal provisioning state 'Failed'.",
"details":[{"code":"RegionIsOfferRestricted",
"message":"Subscriptions are restricted from provisioning in this region.
Please choose a different region.
For exceptions to this rule please open a support request with Issue type of 'Service and subscription limits'.
See https://review.learn.microsoft.com/en-us/azure/postgresql/flexible-server/how-to-request-quota-increase for more details."}]}]}}
```

8. リソースのデプロイが完了したら、Cloud Shell ウィンドウを閉じます。

## Azure Cloud Shell で psql を使用してデータベースに接続する

このタスクでは、[Azure Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/overview) から [psql コマンドラインユーティリティ](https://www.postgresql.org/docs/current/app-psql.html)を使用して、Azure Database for PostgreSQL Flexible Server 上の `rentals` データベースに接続します。

1. [Azure portal](https://portal.azure.com/) で、新しく作成した Azure Database for PostgreSQL Flexible Server に移動します。

2. リソースメニューの \[**設定**\] で \[**データベース**\] を選択し、`rentals` データベースの \[**接続**\] を選択します。
![Connect via psql](12-postgresql-rentals-database-connect.png)

3. Cloud Shell の \[Password for user pgAdmin\] プロンプトで、**pgAdmin** ログイン用にランダムに生成されたパスワードを入力します  。
ログインすると、`rentals` データベースの `psql` プロンプトが表示されます。

4. この演習の残りの部分では、Cloud Shell で作業を続けるため、ウィンドウの右上にある \[**最大化**\] ボタンを選択して、ブラウザー ウィンドウ内のウィンドウを展開すると便利な場合があります。

![Cloud Shell](12-azure-cloud-shell-pane-maximize.png)

## セットアップ: 拡張機能を設定する

ベクターを格納してクエリを実行し、埋め込みを生成するには、Azure Database for PostgreSQL Flexible Server の2つの拡張機能 (`vector` と `azure_ai`) を許可リストに登録し、有効にする必要があります。

1. 両方の拡張機能を許可リストに登録するには、「[PostgreSQL 拡張機能の使用方法](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-extensions#how-to-use-postgresql-extensions)」に記載されている手順に従って、`vector` と `azure_ai` をサーバーパラメーター `azure.extensions` に追加します。

2. 次の SQL コマンドを実行して、`vector` 拡張機能を有効にします。詳細な手順については、「[Azure Database for PostgreSQL Flexible Server で `pgvector` を有効にして使用する方法](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/how-to-use-pgvector#enable-extension)」を参照してください。

```sql
CREATE EXTENSION vector;
```

3. `azure_ai` 拡張機能を有効にするには、次の SQL コマンドを実行します。Azure OpenAI リソースのエンドポイントと API キーが必要です。詳細な手順については、「[`azure_ai` 拡張機能を有効にする](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/generative-ai-azure-overview#enable-the-azure_ai-extension)」を参照してください。

```sql
CREATE EXTENSION azure_ai;
 SELECT azure_ai.set_setting('azure_openai.endpoint', 'https://<endpoint>.openai.azure.com');
 SELECT azure_ai.set_setting('azure_openai.subscription_key', '<API Key>');
```

## データベースにサンプルデータを取り込む

`azure_ai` 拡張機能を調べる前に、`rentals` データベースにいくつかのテーブルを追加し、サンプルデータを設定して、拡張機能の機能を確認するときに操作する情報を用意します。

1. 次のコマンドを実行して、賃貸物件のリストと顧客レビューのデータを格納するための `listings` と `reviews` のテーブルを作成します:

```sql
DROP TABLE IF EXISTS listings;
    
CREATE TABLE listings (
  id int,
  name varchar(100),
  description text,
  property_type varchar(25),
  room_type varchar(30),
  price numeric,
  weekly_price numeric
);
```

```sql
DROP TABLE IF EXISTS reviews;

CREATE TABLE reviews (
  id int,
  listing_id int, 
  date date,
  comments text
);
```

2. 次に、`COPY` コマンドを使用して、上記で作成した各テーブルに CSV ファイルからデータをロードします。まず、次のコマンドを実行して `listings` テーブルにデータを入力します:

```sql
\COPY listings FROM 'mslearn-postgresql/Allfiles/Labs/Shared/listings.csv' CSV HEADER
```

コマンド出力は `COPY 50` で、CSV ファイルからテーブルに 50 行が書き込まれたことを示します。

3. 最後に、以下のコマンドを実行して、カスタマーレビューを `reviews` テーブルにロードします:

```sql
\COPY reviews FROM 'mslearn-postgresql/Allfiles/Labs/Shared/reviews.csv' CSV HEADER
```

コマンド出力は `COPY 354` で、CSV ファイルからテーブルに 354 行が書き込まれたことを示します。

## 埋め込みベクターの作成と保存

サンプルデータがいくつか用意できたので、次は埋め込みベクターを生成して保存します。`azure_ai` 拡張機能を使用すると、Azure OpenAI 埋め込み API を簡単に呼び出すことができます。

1. 埋め込みベクター列を追加します。

`text-embedding-ada-002` モデルは1,536次元を返すように構成されているため、ベクター列のサイズにはそれを使用します。

```sql
ALTER TABLE listings ADD COLUMN listing_vector vector(1536);
```

2. `azure_ai` 拡張機能によって実装される `create_embeddings` ユーザー定義関数を使用して Azure OpenAI を呼び出すことで、各リストの説明の埋め込みベクターを生成します:

```sql
UPDATE listings
 SET listing_vector = azure_openai.create_embeddings('embedding', description, max_attempts => 5, retry_delay_ms => 500)
 WHERE listing_vector IS NULL;
```

使用可能なクォータによっては、数分かかる場合があります。

3. このクエリを実行してベクターの例を参照してください:

```sql
SELECT listing_vector FROM listings LIMIT 1;
```

これに似た結果が得られますが、1536個のベクター列があります:

```sql
postgres=> SELECT listing_vector FROM listings LIMIT 1;
 -[ RECORD 1 ]--+------ ...
 listing_vector | [-0.0018742813,-0.04530062,0.055145424, ... ]
```

## セマンティック検索クエリを実行する

埋め込みベクターで拡張されたリストデータが用意できたので、次はセマンティック検索クエリを実行します。
これを行うには、クエリ文字列埋め込みベクターを取得し、コサイン検索を実行して、説明がクエリと意味的に最も類似しているリストを見つけます。

1. クエリ文字列の埋め込みを生成します。

```sql
SELECT azure_openai.create_embeddings('embedding', 'bright natural light');
```

このような結果が得られます:

```sql
 -[ RECORD 1 ]-----+-- ...
 create_embeddings | {-0.0020871465,-0.002830255,0.030923981, ...}
```

2. コサイン検索(`<=>` はコサイン距離演算を表します)で埋め込みを使用し、クエリに最も類似した上位10のリストをフェッチします。

```sql
SELECT id, name FROM listings
  ORDER BY listing_vector <=> azure_openai.create_embeddings('embedding', 'bright natural light')::vector LIMIT 10;
```

次のような結果が得られます。埋め込みベクターが決定論的であるとは限らないため、結果は異なる場合があります:

```sql
    id    |                name                
 ----------+-------------------------------------
  6796336  | A duplex near U district!
  7635966  | Modern Capitol Hill Apartment
  7011200  | Bright 1 bd w deck. Great location
  8099917  | The Ravenna Apartment
  10211928 | Charming Ravenna Bungalow
  692671   | Sun Drenched Ballard Apartment
  7574864  | Modern Greenlake Getaway
  7807658  | Top Floor Corner Apt-Downtown View
  10265391 | Art filled, quiet, walkable Seattle
  5578943  | Madrona Studio w/Private Entrance
```

3. また、`description` 列を射影して、説明が意味的に類似している一致する行のテキストを読み取ることもできます。たとえば、次のクエリは最適な一致を返します:

```sql
SELECT id, description FROM listings
  ORDER BY listing_vector <=> azure_openai.create_embeddings('embedding', 'bright natural light')::vector LIMIT 1;
```

これは次のようなものを出力します:

```sql
    id    | description
 ---------+------------
  6796336 | This is a great place to live for summer because you get a lot of sunlight at the living room.
  A huge living room space with comfy couch and one ceiling window and glass windows around the living room.
```

セマンティック検索を直感的に理解するには、説明に "bright" や "natural" という用語が実際には含まれていないことに注意してください。
しかし、"summer" と "sunlight"、"windows"、そして "ceiling window" を強調しています。

## 作業内容を確認する

上記の手順を実行すると、`listings` テーブルには、Kaggle の[Seattle Airbnb Open Data](https://www.kaggle.com/datasets/airbnb/seattle/data?select=listings.csv) のサンプルデータが含まれます。リストは、セマンティック検索を実行するための埋め込みベクターで拡張されました。

1. `listings` テーブルに id、name、description、listing_vector の 4 つの列があることを確認します。

```sql
\d listings
```

次のようなものが出力されるはずです:

```sql
                         Table "public.listings"
       Column    |         Type           | Collation | Nullable | Default 
 ----------------+------------------------+-----------+----------+---------
   id            | integer                |           | not null | 
   name          | character varying(255) |           | not null | 
   description   | text                   |           | not null | 
  listing_vector | vector(1536)           |           |          | 
  Indexes:
     "listings_pkey" PRIMARY KEY, btree (id)
```

2. 少なくとも 1 つの行に `listing_vector` 列が設定されていることを確認します。

```sql
SELECT COUNT(*) > 0 FROM listings WHERE listing_vector IS NOT NULL;
```

結果は、真を意味する `t` を表示するはずです。対応する `description` 列が埋め込まれた行が少なくとも 1 つあることを示します:

```sql
 ?column? 
 ----------
 t
 (1 row)
```

埋め込みベクターの次元が 1536 であることを確認します:

```sql
SELECT vector_dims(listing_vector) FROM listings WHERE listing_vector IS NOT NULL LIMIT 1;
```

結果:

```sql
 vector_dims 
 -------------
         1536
 (1 row)
```

3. セマンティック検索で結果が返されることを確認します。
コサイン検索で埋め込みを使用して、クエリに最も類似した上位 10 個のリストを取得します。

```sql
SELECT id, name FROM listings
  ORDER BY listing_vector <=> azure_openai.create_embeddings('embedding', 'bright natural light')::vector LIMIT 10;
```

埋め込みベクターが割り当てられた行に応じて、このような結果が得られます:

```sql
  id |                name                
 --------+-------------------------------------
  315120 | Large, comfy, light, garden studio
  429453 | Sunny Bedroom #2 w/View: Wallingfrd
  17951  | West Seattle, The Starlight Studio
  48848  | green suite seattle - dog friendly
  116221 | Modern, Light-Filled Fremont Flat
  206781 | Bright & Spacious Studio
  356566 | Sunny Bedroom w/View: Wallingford
  9419   | Golden Sun vintage warm/sunny
  136480 | Bright Cheery Room in Seattle House
  180939 | Central District Green GardenStudio
```

## クリーンアップ

この演習を完了したら、作成した Azure リソースを削除します。データベースの使用量ではなく、構成された容量に対して課金されます。次の手順に従って、リソース グループと、このラボ用に作成したすべてのリソースを削除します。
> [!NOTE]
> このラーニング パスで追加のモジュールを完了する予定がある場合は、完了する予定のすべてのモジュールを完了するまで、このタスクをスキップできます。

1. Web ブラウザーを開いて [Azure portal](https://portal.azure.com/) に移動し、ホームページで Azure サービスの\[**リソースグループ**\]を選択します。

![Select RG](12-azure-portal-home-azure-services-resource-groups.png)

2. 任意のフィールドの検索ボックスに、このラボ用に作成したリソースグループの名前を入力し、一覧からリソースグループを選択します。

3. リソースグループの\[**概要**\]ページで、\[**リソース グループの削除**\]を選択します。

![Delete RG](12-resource-group-delete.png)

4. 確認ダイアログで、削除するリソース グループ名を入力して確認し、\[**削除**\]を選択します。
