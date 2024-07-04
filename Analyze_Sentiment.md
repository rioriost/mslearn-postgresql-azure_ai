[翻訳元](https://microsoftlearning.github.io/mslearn-postgresql/Instructions/Labs/16-analyze-sentiment.html)

# 感情を分析する

Margie's Travel 用に構築している AI 搭載アプリの一部として、特定の賃貸物件の個々のレビューの感情とすべてのレビューの全体的な感情に関する情報をユーザーに提供したいと考えています。これを実現するには、Azure Database for PostgreSQL Flexible Server の `azure_ai` 拡張機能を使用して、感情分析機能をデータベースに統合します。

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

## azure_ai 拡張機能のインストールと構成 

`azure_ai` 拡張機能を使用する前に、拡張機能をデータベースにインストールし、Azure AI Services リソースに接続するように構成する必要があります。`azure_ai` 拡張機能を使用すると、Azure OpenAI と Azure AI Language サービスをデータベースに統合できます。データベースで拡張機能を有効にするには、次の手順を実行します:

1. `psql` プロンプトで次のコマンドを実行して、環境の設定時に実行した Bicep デプロイスクリプトによって、`azure_ai` 拡張機能と `vector` 拡張機能がサーバーの許可リストに正常に追加されたことを確認します:

```sql
SHOW azure.extensions;
```

このコマンドは、サーバーの許可リストにある拡張機能のリストを表示します。すべてが正しくインストールされた場合、出力には次のように `azure_ai` と `vector` が含まれている必要があります:

```sql
  azure.extensions 
 ------------------
  azure_ai,vector
```

拡張機能を Azure Database for PostgreSQL Flexible Serverデータベースにインストールして使用する前に、「[PostgreSQL 拡張機能の使用方法](https://learn.microsoft.com/azure/postgresql/flexible-server/concepts-extensions#how-to-use-postgresql-extensions)」の説明に従って、サーバーの許可リストに追加する必要があります。

2. これで、[CREATE EXTENSION](https://www.postgresql.org/docs/current/sql-createextension.html) コマンドを使用して `azure_ai` 拡張機能をインストールする準備が整いました。

```sql
CREATE EXTENSION IF NOT EXISTS azure_ai;
```

`CREATE EXTENSION` は、スクリプトファイルを実行して、新しい拡張機能をデータベースにロードします。このスクリプトは、通常、関数、データ型、スキーマなどの新しい SQL オブジェクトを作成します。同じ名前の拡張機能が既に存在する場合は、エラーがスローされます。`IF NOT EXISTS` を追加すると、コマンドが既にインストールされている場合にエラーをスローせずに実行できます。

## Azure AI Services アカウントと接続する

`azure_ai` 拡張機能の `azure_cognitive` スキーマに含まれる Azure AI サービス統合は、データベースから直接アクセスできる豊富な AI 言語機能のセットを提供します。テキスト要約機能は、[Azure AI Language サービス](https://learn.microsoft.com/azure/ai-services/language-service/overview)を通じて有効になります。

1. `azure_openai` 関数と同様に、`azure_ai` 拡張機能を使用して Azure AI Services に対して呼び出しを正常に行うには、Azure AI Language サービスのエンドポイントとキーを指定する必要があります。Cloud Shell が開いているのと同じブラウザー タブを使用して、Cloud Shell ウィンドウを最小化または復元し、[Azure portal](https://portal.azure.com/) で Language サービスリソースに移動します。リソース メニューの\[**リソース管理**\]セクションで、\[**キーとエンドポイント**\]を選択します。

![Key for cognitive](12-azure-language-service-keys-and-endpoints.png)

> [!NOTE]
> 先に `azure_ai` 拡張機能をインストールし、Language サービスのエンドポイントとキーを事前に設定した際に、`NOTICE: extension "azure_ai" already exists, skipping CREATE EXTENSION` というメッセージが表示された場合は、`azure_ai.get_setting()` 関数を使用して、これらの設定が正しいことを確認し、正しい場合は手順 2 をスキップできます。

2. エンドポイントとアクセスキーの値をコピーし、次のコマンドで、`{endpoint}` トークンと `{api-key}` トークンを Azure portal からコピーした値に置き換えます。Cloud Shell の `psql` コマンドプロンプトからコマンドを実行して、値を `azure_ai.settings` テーブルに追加します。

```sql
SELECT azure_ai.set_setting('azure_cognitive.endpoint', '{endpoint}');
```

```sql
SELECT azure_ai.set_setting('azure_cognitive.subscription_key', '{api-key}');
```

## 拡張機能の感情分析機能を確認する

このタスクでは、`azure_cognitive.analyze_sentiment()` 関数を使用して、賃貸物件リストのレビューを評価します。

1. この演習の残りの部分では、Cloud Shell で作業を続けるため、ウィンドウの右上にある \[**最大化**\] ボタンを選択して、ブラウザー ウィンドウ内のウィンドウを展開すると便利な場合があります。

![Cloud Shell](12-azure-cloud-shell-pane-maximize.png)

2. Cloud Shell で `psql` を操作する場合、クエリ結果の拡張表示を有効にすると、後続のコマンドの出力の読みやすさが向上するため、役立つ場合があります。次のコマンドを実行して、拡張表示を自動的に適用できるようにします。

```sql
\x auto
```

3. `azure_ai` 拡張機能の感情分析機能は、`azure_cognitive` スキーマ内にあります。`analyze_sentiment()` 関数を使用します。[`\df` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DF-LC)を使用して、関数を調べるには、次のコマンドを実行します:

```sql
\df azure_cognitive.analyze_sentiment
```

メタコマンドの出力には、関数のスキーマ、名前、結果のデータ型、および引数が表示されます。この情報は、クエリから関数を操作する方法を理解するのに役立ちます。

出力には `analyze_sentiment()` 関数の 3 つのオーバーロードが表示され、それらの違いを確認できます。出力の `Argument データ型`プロパティは、3 つの関数オーバーロードが想定する引数の一覧を示します:

| 引数 | データ型 | デフォルト値 | 説明 |
| --- | --- | --- | --- |
|text | `text` または `text\[\]` |  | 感情を分析するテキスト (またはテキストの配列)。 |
|language_text | `text` または `text\[\]` |  | 感情を分析するテキストの言語を表す言語コード (または言語コードの配列)。[サポートされている言語の一覧](https://learn.microsoft.com/azure/ai-services/language-service/sentiment-opinion-mining/language-support)を確認して、必要な言語コードを取得します。 |
|batch_size | `integer` | 25 | `text[]` の入力を期待する 2 つのオーバーロードの場合のみ。一度に処理するレコードの数を指定します。 |
|disable_service_logs | `boolean` | false | サービスログをオフにするかどうかを示すフラグ。 |
|timeout_ms | `integer` | 3600000 | 操作が停止するまでのタイムアウト (ミリ秒単位)。|
|throw_on_error | `boolean` | true | 関数がエラー時に例外をスローして、ラップしているトランザクションをロールバックするかどうかを示すフラグ。|
|max_attempts | `integer` | 1 | 障害発生時に Azure OpenAI サービスの呼び出しを再試行する回数。|
|retry_delay_ms | `integer` | 1000 | Azure OpenAI サービス エンドポイントの呼び出しを再試行するまでに待機する時間 (ミリ秒単位)。|

4. また、クエリで出力を正しく処理できるように、関数が返すデータ型の構造を理解することも不可欠です。次のコマンドを実行して、`sentiment_analysis_result` の種類を調べます:

```sql
\dT+ azure_cognitive.sentiment_analysis_result
```

5. 上記のコマンドの出力は、`sentiment_analysis_result` 型が `tuple` であることを示しています。次のコマンドを実行して、`sentiment_analysis_result`型に含まれる列を調べることで、その `tuple` の構造をさらに掘り下げることができます:

```sql
\d+ azure_cognitive.sentiment_analysis_result
```

このコマンドの出力は、次のようになります:

```sql
                  Composite type "azure_cognitive.sentiment_analysis_result"
      Column     |     Type         | Collation | Nullable | Default | Storage  | Description 
 ----------------+------------------+-----------+----------+---------+----------+-------------
  sentiment      | text             |           |          |         | extended | 
  positive_score | double precision |           |          |         | plain    | 
  neutral_score  | double precision |           |          |         | plain    | 
  negative_score | double precision |           |          |         | plain    |
```

`azure_cognitive.sentiment_analysis_result` は、入力テキストの感情予測を含む複合型です。これには、肯定的、否定的、中立的、または混合の感情と、テキストで見つかった肯定的、中立的、否定的な側面のスコアが含まれます。スコアは、0 から 1 までの実数で表されます。たとえば、(中立、0.26、0.64、0.09)の場合、感情は中立で、正のスコアは0.26、中立のスコアは0.64、負のスコアは0.09です。

## レビューの感情を分析する

1. `analyze_sentiment()` 関数とそれが返す `sentiment_analysis_result` を確認したので、関数を使用してみましょう。次の単純なクエリを実行して、`reviews` テーブル内の少数のコメントに対して感情分析を実行します:

```sql
SELECT
  id,
  azure_cognitive.analyze_sentiment(comments, 'en') AS sentiment
FROM reviews
WHERE id <= 10
ORDER BY id;
```

分析した 2 つのレコードから、出力の `sentiment` 値 `(mixed,0.71,0.09,0.2)` と `(positive,0.99,0.01,0)` に注目します。これらは、上記のクエリの `analyze_sentiment()` 関数によって返される `sentiment_analysis_result` を表します。分析は、`reviews` テーブルの `comments` フィールドに対して実行されました。

> [!NOTE]
> `analyze_sentiment()` 関数をインラインで使用すると、クエリ内のテキストの感情をすばやく分析できます。これは少数のレコードではうまく機能しますが、多数のレコードの感情を分析したり、数万件以上のレビューを含む可能性のあるテーブル内のすべてのレコードを更新したりするには理想的ではない場合があります。

2. 長いレビューに役立つ別のアプローチは、その中の各文の感情を分析することです。これを行うには、テキストの配列を受け入れる `analyze_sentiment()` 関数のオーバーロードを使用します。

```sql
SELECT
  azure_cognitive.analyze_sentiment(ARRAY_REMOVE(STRING_TO_ARRAY(comments, '.'), ''), 'en') AS sentence_sentiments
FROM reviews
WHERE id = 1;
```

上記のクエリでは、PostgreSQL の `STRING_TO_ARRAY` 関数を使用しました。さらに、`ARRAY_REMOVE` 関数は、`analyze_sentiment()` 関数でエラーが発生するため、空の文字列である配列要素を削除するために使用されました。

クエリからの出力により、レビュー全体に割り当てられた `mixed` な感情をよりよく理解できます。文章は、肯定的、中立的、否定的な感情が混在しています。

3. 前の 2 つのクエリは、クエリから直接 `sentiment_analysis_result` を返しました。ただし、`sentiment_analysis_result` `tuple` 内の基になる値を取得することをお勧めします。圧倒的に肯定的なレビューを探し、感情のコンポーネントを個々のフィールドに抽出する次のクエリを実行します:

```sql
WITH cte AS (
  SELECT id, comments, azure_cognitive.analyze_sentiment(comments, 'en') AS sentiment FROM reviews
)
SELECT
  id,
  (sentiment).sentiment,
  (sentiment).positive_score,
  (sentiment).neutral_score,
  (sentiment).negative_score,
  comments
FROM cte
WHERE (sentiment).positive_score > 0.98
LIMIT 5;
```

上記のクエリでは、共通テーブル式または CTE を使用して、`reviews` テーブル内のすべてのレコードの `sentiment` スコアを取得します。次に、CTE によって返された `sentiment_analysis_result` から感情複合型の列を選択して、`tuple`から個々の値を抽出します。

## Reviews テーブルに感情を保存する

Margie's Travel 用に構築している賃貸物件のレコメンデーション システムでは、感情評価が要求されるたびに電話をかけたり、費用が発生したりしなくて済むように、感情評価をデータベースに保存したいと考えています。感情分析をその場で実行すると、少数のレコードや、ほぼリアルタイムでのデータ分析に大きく役立ちます。それでも、アプリケーションで使用するために感情データをデータベースに追加することは、保存されているレビューにとって理にかなっています。これを行うには、`reviews` テーブルを変更して、感情評価と肯定的、中立的、否定的なスコアを格納するための列を追加します。

1. 次のクエリを実行して `reviews` テーブルを更新し、感情の詳細を格納できるようにしま:

```sql
ALTER TABLE reviews
ADD COLUMN sentiment varchar(10),
ADD COLUMN positive_score numeric,
ADD COLUMN neutral_score numeric,
ADD COLUMN negative_score numeric;
```

2. 次に、reviews テーブルの既存のレコードを、感情値と関連するスコアで更新します。

```sql
WITH cte AS (
　　SELECT id, azure_cognitive.analyze_sentiment(comments, 'en') AS sentiment FROM reviews
)
UPDATE reviews AS r
SET
　　sentiment = (cte.sentiment).sentiment,
　　positive_score = (cte.sentiment).positive_score,
　　neutral_score = (cte.sentiment).neutral_score,
　　negative_score = (cte.sentiment).negative_score
FROM cte
WHERE r.id = cte.id;
```

このクエリの実行には、テーブル内のすべてのレビューのコメントが分析のために Language サービスのエンドポイントに個別に送信されるため、長い時間がかかります。レコードをバッチで送信すると、多数のレコードを処理する場合に効率的になります。

3. 以下のクエリを実行して同じ更新アクションを実行しますが、今回は `reviews` テーブルからコメントを10個のバッチで送信し(これは許容される最大バッチサイズです)、パフォーマンスの違いを評価します。

```sql
WITH cte AS (
  SELECT azure_cognitive.analyze_sentiment(ARRAY(SELECT comments FROM reviews ORDER BY id), 'en', batch_size => 10) as sentiments
),
sentiment_cte AS (
  SELECT
    ROW_NUMBER() OVER () AS id,
    sentiments AS sentiment
  FROM cte
)
UPDATE reviews AS r
SET
  sentiment = (sentiment_cte.sentiment).sentiment,
  positive_score = (sentiment_cte.sentiment).positive_score,
  neutral_score = (sentiment_cte.sentiment).neutral_score,
  negative_score = (sentiment_cte.sentiment).negative_score
FROM sentiment_cte
WHERE r.id = sentiment_cte.id;
```

このクエリは 2 つの CTE を使用しており少し複雑ですが、パフォーマンスははるかに向上します。このクエリでは、最初の CTE はレビュー コメントのバッチの感情を分析し、2 番目の CTE は、順位と各行の 'sentiment_analysis_result' に基づく `id` を含む新しいテーブルに `sentiment_analysis_results` テーブルからの結果を抽出します。その後、2 番目の CTE を `UPDATE` ステートメントで使用して、値をデータベースに書き込むことができます。

4. 次に、クエリを実行して更新結果を観察し、**否定的**な感情を持つレビューを、最も否定的なものから順に検索します。

```sql
SELECT
  id,
  negative_score,
  comments
FROM reviews
WHERE sentiment = 'negative'
ORDER BY negative_score DESC;
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
