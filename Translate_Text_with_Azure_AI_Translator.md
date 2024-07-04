[翻訳元](https://microsoftlearning.github.io/mslearn-postgresql/Instructions/Labs/18-translate-text.html)

# Azure AI Translator でテキストを翻訳する

Margie's Travelの主任開発者として、あなたは国際化の取り組みを支援するように求められました。
現在、同社の短期レンタルサービスの賃貸物件はすべて英語で書かれています。
これらのリストを、大規模な開発作業なしでさまざまな言語に翻訳する必要があります。
すべてのデータが Azure Database for PostgreSQL Flexible Server でホストされており、Azure AI Services を使用して翻訳を実行したいと考えています。
この演習では、Azure Database for PostgreSQL Flexible Server データベースを介して Azure AI Translator サービスを使用して、英語のテキストをさまざまな言語に翻訳します。

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

## リストデータをデータベースに取り込む

翻訳するには、英語のリストデータを用意する必要があります。前のモジュールで `rentals` データベースに `listings` テーブルを作成していない場合は、次の手順に従って作成します。

1. 次のコマンドを実行して、賃貸物件のリストデータを格納するための `listings` テーブルを作成します:

```sql
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

2. 次に、`COPY` コマンドを使用して、CSV ファイルから上記で作成した各テーブルにデータをロードします。まず、次のコマンドを実行して、`listings` テーブルにデータを入力します:

```sql
\COPY listings FROM 'mslearn-postgresql/Allfiles/Labs/Shared/listings.csv' CSV HEADER
```

コマンド出力は `COPY 50` で、CSV ファイルから 50 行がテーブルに書き込まれたことを示します。

## 翻訳用の追加のテーブルを作成する

`listings` データを用意しましたが、変換を行うにはさらに2つのテーブルが必要です。

1. 次のコマンドを実行して、`languages` テーブルと `listing_translations` テーブルを作成します。

```sql
CREATE TABLE languages (
  code VARCHAR(7) NOT NULL PRIMARY KEY
);
```

```sql
CREATE TABLE listing_translations(
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  listing_id INT,
  language_code VARCHAR(7),
  description TEXT
);
```

2. 次に、翻訳する言語ごとに1行ずつ挿入します。ここでは、ドイツ語、簡体字中国語、ヒンディー語、ハンガリー語、スワヒリ語の 5 つの言語の行を作成します。

```sql
INSERT INTO languages(code)
VALUES
  ('de'),
  ('zh-Hans'),
  ('hi'),
  ('hu'),
  ('sw');
```

コマンド出力は `INSERT 0 5` で、表に 5 つの新しい行を挿入したことを示します。

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

3. 次に、`azure_ai.set_setting()` 関数を使用して、Azure AI Translator サービスへの接続を構成する必要があります。Cloud Shell が開いているのと同じブラウザー タブを使用して、Cloud Shell ウィンドウを最小化または復元してから、[Azure portal](https://portal.azure.com/) で Azure AI Translator リソースに移動します。Azure AI Translator リソース ページに移動したら、リソース メニューの [**リソース管理**] セクションで [**キーとエンドポイント**] を選択し、使用可能なキーの 1 つ、リージョン、ドキュメント翻訳エンドポイントをコピーします。

![Keys and endpoint for translator services](18-azure-ai-translator-keys-and-endpoint.png)

`KEY 1` または `KEY 2` のいずれかを使用できます。常に2つのキーを持つことで、サービスを中断することなく、キーを安全にローテーションおよび再生成できます。

4. AI Translator エンドポイント、サブスクリプション キー、リージョンを指すように `azure_cognitive` 設定を構成します。`azure_cognitive.endpoint` の値は、サービスのドキュメント翻訳 URL になります。`azure_cognitive.subscription_key` の値は、KEY 1 または KEY 2 になります。`azure_cognitive.region` の値は、Azure AI Translator インスタンスのリージョンになります。

```sql
SELECT azure_ai.set_setting('azure_cognitive.endpoint','https://<YOUR_ENDPOINT>.cognitiveservices.azure.com/');
SELECT azure_ai.set_setting('azure_cognitive.subscription_key', '<YOUR_KEY>');
SELECT azure_ai.set_setting('azure_cognitive.region', '<YOUR_REGION>');
```

## リストデータを変換するストアドプロシージャを作成する

言語翻訳テーブルにデータを取り込むには、データをバッチで読み込むストアド プロシージャを作成します。

1. `psql` プロンプトで次のコマンドを実行して、`translate_listing_descriptions` という名前の新しいストアド プロシージャを作成します。

```sql
CREATE OR REPLACE PROCEDURE translate_listing_descriptions(max_num_listings INT DEFAULT 10)
LANGUAGE plpgsql
AS $$
BEGIN
  WITH batch_to_load(id, description) AS
  (
    SELECT id, description
    FROM listings l
    WHERE NOT EXISTS (SELECT * FROM listing_translations ll WHERE ll.listing_id = l.id)
    LIMIT max_num_listings
  )
  INSERT INTO listing_translations(listing_id, language_code, description)
  SELECT b.id, l.code, (unnest(tr.translations)).TEXT
  FROM batch_to_load b
    CROSS JOIN languages l
    CROSS JOIN LATERAL azure_cognitive.translate(b.description, l.code) tr;
END;
$$;
```

このストアドプロシージャは、5つのレコードのバッチをロードし、選択した各言語で説明を翻訳し、翻訳された説明を `listing_translations` テーブルに挿入します。

2. 次の SQL コマンドを使用してストアドプロシージャを実行します:

```sql
CALL translate_listing_descriptions(10);
```

この呼び出しは、レンタルリストごとに 5 つの言語に翻訳するのに約 1 秒かかるため、各実行には約 10 秒かかります。コマンド出力は `CALL` で、ストアドプロシージャの呼び出しが成功したことを示します。

3. ストアド プロシージャをさらに 4 回呼び出し、このプロシージャを 5 回呼び出します。これにより、テーブル内のすべてのリストに対して翻訳が生成されます。

4. 次のスクリプトを実行して、リスト翻訳の数を取得します。

```sql
SELECT COUNT(*) FROM listing_translations;
```

この呼び出しは、各リストが 5 つの言語に翻訳されたことを示す値 250 を返すはずです。`listing_translations` テーブルをクエリすることで、データをさらに分析できます。

## 翻訳付きの新しいリストを追加するプロシージャを作成する

既存のリストを翻訳するストアドプロシージャがありますが、国際化計画では、新しいリストが入力されたときに翻訳する必要もあります。これを行うには、別のストアド プロシージャを作成します。

1. `psql` プロンプトで次のコマンドを実行して、`add_listing` という名前の新しいストアド プロシージャを作成します。

```sql
CREATE OR REPLACE PROCEDURE add_listing(id INT, name VARCHAR(255), description TEXT)
LANGUAGE plpgsql
AS $$
DECLARE
listing_id INT;
BEGIN
  INSERT INTO listings(id, name, description)
  VALUES(id, name, description);

  INSERT INTO listing_translations(listing_id, language_code, description)
  SELECT id, l.code, (unnest(tr.translations)).TEXT
  FROM languages l
    CROSS JOIN LATERAL azure_cognitive.translate(description, l.code) tr;
END;
$$;
```

このストアドプロシージャは、`listings` テーブルに行を挿入します。次に、`language` テーブル内の各言語の説明を翻訳し、これらの翻訳を `listing_translations` テーブルに挿入します。

2. 次の SQL コマンドを使用してストアドプロシージャを実行します:

```sql
CALL add_listing(51, 'A Beautiful Home', 'This is a beautiful home in a great location.');
```

コマンド出力は `CALL` で、ストアドプロシージャの呼び出しが成功したことを示します。

3. 次のスクリプトを実行して、新しいリストの翻訳を取得します。

```sql
SELECT l.id, l.name, l.description, lt.language_code, lt.description AS translated_description
FROM listing_translations lt
  INNER JOIN listings l ON lt.listing_id = l.id
WHERE l.name = 'A Beautiful Home';
```

呼び出しは、次の表のような値を持つ 5 行を返します。

```sql
  id  | listing_id | language_code |                    description                     
 -----+------------+---------------+------------------------------------------------------
  126 |          2 | de            | Dies ist ein schönes Haus in einer großartigen Lage.
  127 |          2 | zh-Hans       | 这是一个美丽的家，地理位置优越。
  128 |          2 | hi            | यह एक महान स्थान में एक सुंदर घर है।
  129 |          2 | hu            | Ez egy gyönyörű otthon egy nagyszerű helyen.
  130 |          2 | sw            | Hii ni nyumba nzuri katika eneo kubwa.
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
