[翻訳元](https://microsoftlearning.github.io/mslearn-postgresql/Instructions/Labs/18-translate-text.html)

# Azure AI Translator でテキストを翻訳する

上場会社は、最も人気のあるフレーズや場所など、市場動向を分析したいと考えていることを思い出してください。
チームはまた、個人を特定できる情報(PII)の保護を強化する予定です。
現在のデータは、Azure Database for PostgreSQL Flexible Server に格納されます。
プロジェクトの予算は少ないため、キーワードやタグを維持するための初期費用と継続的なコストを最小限に抑えることが不可欠です。
開発者は、PIIが使用できるフォームの数を警戒しており、社内の正規表現マッチャーよりも費用対効果が高く、吟味されたソリューションを好みます。

`azure_ai` 拡張機能を使用して、データベースを Azure AI Language サービスと統合します。
この拡張機能は、ユーザー定義の SQL 関数 API を、次のようないくつかの Azure Cognitive Service API に提供します:

* キーフレーズ抽出
* 名前付きエンティティ認識
* PII 検出

このアプローチにより、データサイエンスチームは、リストの注目度データにすばやく着目して、市場の傾向を判断できます。
また、アプリケーション開発者に、アクセスを必要としない状況で提示するための PII セーフテキストを提供します。
識別されたエンティティを格納することで、問い合わせや誤検知の PII 認識 (PII ではないものの PII であると考える) の場合に、人間によるレビューが可能になります。

最後に、`listings` テーブルに 4 つの新しい列があり、分析情報が抽出されます:

* `key_phrases`
* `recognized_entities`
* `pii_safe_description`
* `pii_entities`

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

Bicep デプロイ スクリプトは、この演習を完了するために必要な Azure サービスをリソースグループにプロビジョニングします。デプロイされるリソースには、Azure Database for PostgreSQL Flexible Server、Azure OpenAI、Azure AI Language サービスが含まれます。また、Bicep スクリプトでは、PostgreSQL サーバーの許可リストへの `azure_ai` 拡張機能と `vector` 拡張機能の追加 (azure.extensions サーバーパラメーターを使用)、サーバー上に `rentals` という名前のデータベースを作成し、`text-embedding-ada-002` モデルを使用する `embedding` という名前のデプロイを Azure OpenAI サービスに追加するなど、いくつかの構成手順も実行されます。Bicep ファイルは、このラーニングパスのすべてのモジュールで共有されるため、一部の演習ではデプロイされたリソースの一部のみを使用できます。

通常、デプロイが完了するまでに数分かかります。Cloud Shell から監視するか、上記で作成したリソースグループの \[**デプロイ**\] ページに移動して、そこでデプロイの進行状況を確認できます。

Bicep デプロイスクリプトの実行時にいくつかのエラーが発生する場合があります。最も一般的なメッセージとその解決手順は次のとおりです:

* Azure AI Services リソースを以前に作成していない場合は、責任ある AI の利用条件が演習で用いるサブスクリプションで未読で同意されていないというメッセージが表示されることがあります:

```
{"code": "ResourceKindRequireAcceptTerms",
"message": "This subscription cannot create TextAnalytics until you agree to Responsible AI terms for this resource.
You can agree to Responsible AI terms by creating a resource through the Azure Portal and trying again."}
```

このエラーを解決するには、Azure portal から最初の言語リソースを作成し、使用条件を確認して承認できるようにする必要があります。ここで行うことができます: [https://portal.azure.com/#create/Microsoft.CognitiveServicesTextAnalytics](https://portal.azure.com/#create/Microsoft.CognitiveServicesTextAnalytics). ランダムで有効な名前を持つ新しいリソースグループの下に作成し、デプロイする Language サービスにランダムで有効な名前を割り当てます。その後、サブスクリプション全体の責任ある AI の条項に同意すると、同じ Azure サブスクリプションで任意のデプロイツール (SDK、CLI、ARM テンプレートなど) を使用して、後続の言語リソースを作成できます。そのため、ポータルで最初のリソースを作成したら、それを削除し、コマンドを再実行して Bicep デプロイスクリプトを実行できます。

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

サンプルデータをリセットするには、`DROP TABLE listings` を実行し、これらの手順を繰り返します。

## キーフレーズを抽出する

1. キーフレーズは、`pg_typeof` 関数によって明らかにされたように、`text[]` として抽出されます:

```sql
SELECT pg_typeof(azure_cognitive.extract_key_phrases('The food was delicious and the staff were wonderful.', 'en-us'));
```

キーの結果を含む列を作成します。

```sql
ALTER TABLE listings ADD COLUMN key_phrases text[];
```

2. 列をバッチで入力します。クォータによっては、`LIMIT` 値を調整することもできます。コマンドは何度でも自由に実行してください。この演習では、すべての行を設定する必要はありません。

```sql
UPDATE listings
SET key_phrases = azure_cognitive.extract_key_phrases(description)
FROM (SELECT id FROM listings WHERE key_phrases IS NULL ORDER BY id LIMIT 100) subset
WHERE listings.id = subset.id;
```

3. キーフレーズを `listings` にクエリする

```sql
SELECT id, name FROM listings WHERE 'market' = ANY(key_phrases);
```

キーフレーズが入力されているリストに応じて、次のような結果が得られます:

```sql
    id    |                name                
 ---------+-------------------------------------
   931154 | Met Tower in Belltown! MT2
   931758 | Hottest Downtown Address, Pool! MT2
  1084046 | Near Pike Place & Space Needle! MT2
  1084084 | The Best of the Best, Seattle! MT2
```

## 名前付きエンティティ認識

1. エンティティは、`pg_typeof` 関数によって明らかにされたように、`azure_cognitive.entity[]` として抽出されます:

```sql
SELECT pg_typeof(azure_cognitive.recognize_entities('For more information, see Cognitive Services Compliance and Privacy notes.', 'en-us'));
```

キーの結果を含む列を作成します。

```sql
 ALTER TABLE listings ADD COLUMN entities azure_cognitive.entity[];
```

2. 列をバッチで入力します。この処理には数分かかる場合があります。クォータに応じて `LIMIT` 値を調整したり、部分的な結果でより迅速に返したりすることもできます。コマンドは何度でも自由に実行してください。この演習では、すべての行を設定する必要はありません。

```sql
UPDATE listings
SET entities = azure_cognitive.recognize_entities(description, 'en-us')
FROM (SELECT id FROM listings WHERE entities IS NULL ORDER BY id LIMIT 500) subset
WHERE listings.id = subset.id;
```

3. これで、すべてのリストのエンティティを照会して、デッキがある物件を見つけることができます:

```sql
SELECT id, name
FROM listings, unnest(entities) e
WHERE e.text LIKE '%roof%deck%'
LIMIT 10;
```

これは次のようなものを返します:

```sql
    id    |                name                
 ---------+-------------------------------------
   430610 | 3br/3ba. modern, roof deck, garage
   430610 | 3br/3ba. modern, roof deck, garage
  1214306 | Private Bed/bath in Home: green (A)
    74328 | Spacious Designer Condo
   938785 | Best Ocean Views By Pike Place! PA1
    23430 | 1 Bedroom Modern Water View Condo
   828298 | 2 Bedroom Sparkling City Oasis
   338043 | large modern unit & fab location
   872152 | Luxurious Local Lifestyle 2Bd/2+Bth
   116221 | Modern, Light-Filled Fremont Flat
```

## PII 検出

1. エンティティは、`pg_typeof` 関数によって明らかにされたように、`azure_cognitive.pii_entity_recognition_result` として抽出されます:

```sql
SELECT pg_typeof(azure_cognitive.recognize_pii_entities('For more information, see Cognitive Services Compliance and Privacy notes.', 'en-us'));
```

この値は、編集されたテキストと PII エンティティの配列を含む複合型です:

```sql
\d azure_cognitive.pii_entity_recognition_result
```

出力:

```sql
      Composite type "azure_cognitive.pii_entity_recognition_result"
      Column    |           Type           | Collation | Nullable | Default 
 ---------------+--------------------------+-----------+----------+---------
  redacted_text | text                     |           |          | 
  entities      | azure_cognitive.entity[] |           |          | 
```

マスクされたテキストを格納する列と、認識されたエンティティの列を作成します:

```sql
ALTER TABLE listings ADD COLUMN description_pii_safe text;
ALTER TABLE listings ADD COLUMN pii_entities azure_cognitive.entity[];
```

2. 列をバッチで入力します。この処理には数分かかる場合があります。クォータに応じて `LIMIT` 値を調整したり、部分的な結果でより迅速に返したりすることもできます。コマンドは何度でも自由に実行してください。この演習では、すべての行を設定する必要はありません。

```sql
UPDATE listings
SET
  description_pii_safe = pii.redacted_text,
  pii_entities = pii.entities
FROM (SELECT id, description FROM listings WHERE description_pii_safe IS NULL OR pii_entities IS NULL ORDER BY id LIMIT 100) subset,
LATERAL azure_cognitive.recognize_pii_entities(subset.description, 'en-us') as pii
WHERE listings.id = subset.id;
```

3. これで、PII の可能性があるものをすべて編集した状態で出品説明を表示できるようになりました:

```sql
SELECT description_pii_safe
FROM listings
WHERE description_pii_safe IS NOT NULL
LIMIT 1;
```

出力:

```sql
A lovely stone-tiled room with kitchenette.
New full mattress futon bed.
Fridge, microwave, kettle for coffee and tea.
Separate entrance into book-lined mudroom.
Large bathroom with Jacuzzi (shared occasionally with ***** to do laundry).
Stone-tiled, radiant heated floor, 300 sq ft room with 3 large windows.
The bed is queen-sized futon and has a full-sized mattress with topper.
Bedside tables and reading lights on both sides.
Also large leather couch with cushions.
Kitchenette is off the side wing of the main room and has a microwave, and fridge, and an electric kettle for making coffee or tea.
Kitchen table with two chairs to use for meals or as desk.
Extra high-speed WiFi is also provided.
Access to English Garden.
The Ballard Neighborhood is a great place to visit: *10 minute walk to downtown Ballard with fabulous bars and restaurants, great ****** farmers market, nice three-screen cinema, and much more.
*5 minute walk to the Ballard Locks, where ships enter and exit Puget Sound
```

4. また、PII で認識されたエンティティを特定することもできます。たとえば、上記と同じリストを使用します:

```sql
SELECT entities
FROM listings
WHERE entities IS NOT NULL
LIMIT 1;
```

出力:

```sql
                         pii_entities                        
 -------------------------------------------------------------
 {"(hosts,PersonType,\"\",0.93)","(Sunday,DateTime,Date,1)"}
```

## 作業を確認する

抽出されたキーフレーズ、認識されたエンティティ、PII が入力されたことを確認しましょう:

1. キーフレーズをチェックする:

```sql
SELECT COUNT(*) FROM listings WHERE key_phrases IS NOT NULL;
```

実行したバッチの数に応じて、次のようなものが表示されます:

```sql
 count 
 -------
  100
```

2. 認識されたエンティティをチェックする:

```sql
SELECT COUNT(*) FROM listings WHERE entities IS NOT NULL;
```

次のように表示されます:

```sql
 count 
 -------
  500
```

3. マスクされた PII をチェックする:

```sql
SELECT COUNT(*) FROM listings WHERE description_pii_safe IS NOT NULL;
```

100 個のバッチを 1 つロードした場合は:

```sql
 count 
 -------
  100
```

PII が検出された出品情報の数を確認できます:

```sql
SELECT COUNT(*) FROM listings WHERE description != description_pii_safe;
```

次のように表示されます:

```sql
 count 
 -------
     87
```

4. 検出された PII エンティティを確認する: 上の結果から、空の PII 配列が13個あるはずです。

```sql
SELECT COUNT(*) FROM listings WHERE pii_entities IS NULL AND description_pii_safe IS NOT NULL;
```

結果:

```sql
 count 
 -------
     13
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
